from __future__ import annotations

import csv
import re
import tempfile
import time
import zipfile
from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, date, datetime
from io import TextIOWrapper
from typing import Any, TextIO

import boto3
from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError, EndpointConnectionError
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.constants import ComplaintChannel, ProcessingStatus
from app.models.complaint import Complaint
from app.schemas.ingestion import (
    S3ComplaintImportFilters,
    S3ComplaintPreviewItem,
    S3ImportLog,
    S3ImportOptionsResponse,
    S3ImportPreviewResponse,
    S3ImportResponse,
    S3SourceSummary,
)


class S3IngestionError(RuntimeError):
    pass


class S3QueryModeRequiredError(S3IngestionError):
    pass


class S3CredentialsMissingError(S3IngestionError):
    pass


class AthenaTimeoutError(S3IngestionError):
    pass


class AthenaTableMissingError(S3IngestionError):
    pass


class NoMatchingRowsError(S3IngestionError):
    pass


class S3SourceUnavailableError(S3IngestionError):
    pass



def _value(row: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return value
    return None


def _text(value: Any, max_length: int | None = None) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    if not cleaned:
        return None
    return cleaned[:max_length] if max_length is not None else cleaned


def _boolean(value: Any) -> bool | None:
    normalized = str(value).strip().lower() if value is not None else ""
    if normalized in {"yes", "y", "true", "1"}:
        return True
    if normalized in {"no", "n", "false", "0"}:
        return False
    return None


def _datetime(value: Any) -> datetime | None:
    text = _text(value)
    if text is None:
        return None
    for candidate in (text.replace("Z", "+00:00"), text):
        try:
            parsed = datetime.fromisoformat(candidate)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
        except ValueError:
            continue
    for fmt in ("%m/%d/%Y", "%Y/%m/%d", "%d/%m/%Y", "%Y-%m-%d"):
        try:
            parsed = datetime.strptime(text, fmt)
            return parsed.replace(tzinfo=UTC)
        except ValueError:
            continue
    return None


def normalize_channel(raw_channel: str | None) -> str:
    if not raw_channel:
        return ComplaintChannel.WEB.value
    cleaned = raw_channel.strip().lower()
    if "web" in cleaned:
        return ComplaintChannel.WEB.value
    if "phone" in cleaned or "call" in cleaned:
        return ComplaintChannel.PHONE.value
    if "email" in cleaned:
        return ComplaintChannel.EMAIL.value
    if "chat" in cleaned or "sms" in cleaned or "social" in cleaned:
        return ComplaintChannel.CHAT.value
    if "manual" in cleaned or "referral" in cleaned or "mail" in cleaned or "fax" in cleaned or "postal" in cleaned:
        return ComplaintChannel.MANUAL.value
    return ComplaintChannel.WEB.value



def map_cfpb_csv_row(row: dict[str, Any]) -> dict[str, Any] | None:
    complaint_id = _text(_value(row, "Complaint ID", "complaint_id"), 128)
    narrative = _text(
        _value(
            row,
            "Consumer complaint narrative",
            "consumer_complaint_narrative",
            "complaint_what_happened",
        )
    )
    if complaint_id is None or narrative is None:
        return None
    raw_channel = _text(_value(row, "Submitted via", "submitted_via"), 64)
    return {
        "id": f"cfpb-{complaint_id}"[:64],
        "source_complaint_id": complaint_id,
        "narrative": narrative,
        "channel": normalize_channel(raw_channel),
        "product": _text(_value(row, "Product", "product"), 255),
        "sub_product": _text(_value(row, "Sub-product", "sub_product"), 255),
        "issue": _text(_value(row, "Issue", "issue"), 255),
        "sub_issue": _text(_value(row, "Sub-issue", "sub_issue"), 255),
        "company": _text(_value(row, "Company", "company"), 255),
        "company_response": _text(
            _value(row, "Company response to consumer", "company_response_to_consumer"),
            255,
        ),
        "timely_response": _boolean(_value(row, "Timely response?", "timely_response")),
        "date_received": _datetime(_value(row, "Date received", "date_received")),
        "ai_status": ProcessingStatus.PENDING.value,
        "retry_count": 0,
    }


def _matches(row: dict[str, Any], filters: S3ComplaintImportFilters) -> bool:
    values = {
        "product": _text(_value(row, "Product", "product")),
        "sub_product": _text(_value(row, "Sub-product", "sub_product")),
        "issue": _text(_value(row, "Issue", "issue")),
        "company": _text(_value(row, "Company", "company")),
        "channel": _text(_value(row, "Submitted via", "submitted_via")),
    }
    for field, actual in values.items():
        selected = getattr(filters, field)
        if selected is not None and actual != selected:
            return False

    timely_response = _boolean(_value(row, "Timely response?", "timely_response"))
    if filters.timely_response is not None and timely_response != filters.timely_response:
        return False

    received = _datetime(_value(row, "Date received", "date_received"))
    received_date = received.date() if received is not None else None
    if filters.date_received_min is not None and (
        received_date is None or received_date < filters.date_received_min
    ):
        return False
    if filters.date_received_max is not None and (
        received_date is None or received_date > filters.date_received_max
    ):
        return False
    return True


class CfpbS3IngestionService:
    def __init__(self, settings: Settings):
        if not settings.s3_bucket_name or not settings.cfpb_s3_key:
            raise S3IngestionError("S3_BUCKET_NAME and CFPB_S3_KEY must be configured.")
        self.bucket = settings.s3_bucket_name
        self.key = settings.cfpb_s3_key
        self.mode = settings.cfpb_ingestion_mode
        self.last_execution_id: str | None = None
        try:
            self.client = boto3.client("s3", region_name=settings.aws_region)
            if self.mode == "athena":
                if not settings.athena_database or not settings.athena_table or not settings.athena_output_location:
                    raise S3IngestionError("Athena ingestion settings are incomplete.")
                self.athena_database = self._identifier(settings.athena_database)
                self.athena_table = self._identifier(settings.athena_table)
                self.athena_output_location = settings.athena_output_location
                self.athena_workgroup = settings.athena_workgroup
                self.athena_timeout_seconds = settings.athena_query_timeout_seconds
                self.athena = boto3.client("athena", region_name=settings.aws_region)
        except (NoCredentialsError, ClientError) as exc:
            raise S3CredentialsMissingError(f"AWS configuration or credentials missing/invalid: {exc}") from exc

    @property
    def source(self) -> S3SourceSummary:
        return S3SourceSummary(label="Private CFPB import source")

    @property
    def query_mode(self) -> str:
        return getattr(self, "mode", "csv")

    @staticmethod
    def _identifier(value: str) -> str:
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value):
            raise S3IngestionError("Athena database and table names must use letters, numbers, and underscores.")
        return value

    @contextmanager
    def _csv_stream(self) -> Generator[TextIO, None, None]:
        key_lower = self.key.lower()
        try:
            if key_lower.endswith(".zip"):
                with tempfile.TemporaryFile() as archive:
                    self.client.download_fileobj(self.bucket, self.key, archive)
                    archive.seek(0)
                    with zipfile.ZipFile(archive) as zip_file:
                        names = [name for name in zip_file.namelist() if name.lower().endswith(".csv")]
                        if not names:
                            raise S3IngestionError("The S3 ZIP file does not contain a CSV file.")
                        with zip_file.open(names[0]) as csv_member:
                            with TextIOWrapper(csv_member, encoding="utf-8-sig", newline="") as text:
                                yield text
                return
            if key_lower.endswith(".csv"):
                response = self.client.get_object(Bucket=self.bucket, Key=self.key)
                body = response["Body"]
                with TextIOWrapper(body, encoding="utf-8-sig", newline="") as text:
                    yield text
                return
            raise S3IngestionError("CFPB_S3_KEY must reference a .csv or .zip object.")
        except NoCredentialsError as exc:
            raise S3CredentialsMissingError("AWS credentials are missing.") from exc
        except EndpointConnectionError as exc:
            raise S3SourceUnavailableError(f"S3 endpoint is unreachable: {exc}") from exc
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code", "")
            if error_code in ("InvalidAccessKeyId", "SignatureDoesNotMatch", "AuthFailure", "AccessDenied", "ExpiredToken"):
                raise S3CredentialsMissingError(f"AWS credentials are invalid: {exc}") from exc
            if error_code in ("NoSuchBucket", "NoSuchKey"):
                raise S3SourceUnavailableError(f"S3 bucket or key does not exist: {exc}") from exc
            raise S3IngestionError(f"S3 Client Error: {exc}") from exc
        except (BotoCoreError, OSError, zipfile.BadZipFile) as exc:
            raise S3IngestionError(f"Unable to read the CFPB object from S3: {exc}") from exc

    def _rows(self) -> Iterator[dict[str, Any]]:
        with self._csv_stream() as stream:
            yield from csv.DictReader(stream)

    @property
    def _athena_source(self) -> str:
        return f'"{self.athena_database}"."{self.athena_table}"'

    @staticmethod
    def _sql_text(value: str) -> str:
        return "'" + value.replace("'", "''") + "'"

    def _athena_where(self, filters: S3ComplaintImportFilters | None = None) -> str:
        clauses = [
            "complaint_id IS NOT NULL",
            "consumer_complaint_narrative IS NOT NULL",
            "trim(consumer_complaint_narrative) <> ''",
        ]
        if filters is None:
            return " AND ".join(clauses)
        for field in ("product", "sub_product", "issue", "company", "channel"):
            selected = getattr(filters, field)
            if selected is None:
                continue
            column = "submitted_via" if field == "channel" else field
            clauses.append(f"{column} = {self._sql_text(selected)}")
            if field == "product":
                clauses.append(f"product_partition = {self._sql_text(selected)}")
        if filters.timely_response is not None:
            true_values = "('yes', 'true', '1')"
            operator = "IN" if filters.timely_response else "NOT IN"
            clauses.append(f"lower(CAST(timely_response AS varchar)) {operator} {true_values}")
        if filters.date_received_min is not None:
            clauses.append(f"date_received >= DATE '{filters.date_received_min.isoformat()}'")
        if filters.date_received_max is not None:
            clauses.append(f"date_received <= DATE '{filters.date_received_max.isoformat()}'")
        return " AND ".join(clauses)

    def _run_athena(self, query: str) -> list[dict[str, str | None]]:
        try:
            started = self.athena.start_query_execution(
                QueryString=query,
                QueryExecutionContext={"Database": self.athena_database},
                ResultConfiguration={"OutputLocation": self.athena_output_location},
                WorkGroup=self.athena_workgroup,
            )
            execution_id = started["QueryExecutionId"]
            self.last_execution_id = execution_id
            deadline = time.monotonic() + self.athena_timeout_seconds
            while True:
                status = self.athena.get_query_execution(QueryExecutionId=execution_id)[
                    "QueryExecution"
                ]["Status"]
                state = status["State"]
                if state == "SUCCEEDED":
                    break
                if state in {"FAILED", "CANCELLED"}:
                    reason = status.get("StateChangeReason", state)
                    reason_lower = reason.lower()
                    if "table not found" in reason_lower or "does not exist" in reason_lower or "table missing" in reason_lower:
                        raise AthenaTableMissingError(f"Athena table or database does not exist: {reason}")
                    raise S3IngestionError(f"Athena query did not complete: {reason}")
                if time.monotonic() >= deadline:
                    self.athena.stop_query_execution(QueryExecutionId=execution_id)
                    raise AthenaTimeoutError("Athena query timed out.")
                time.sleep(0.2)

            output: list[dict[str, str | None]] = []
            headers: list[str] | None = None
            token: str | None = None
            while True:
                kwargs: dict[str, str] = {"QueryExecutionId": execution_id}
                if token:
                    kwargs["NextToken"] = token
                result = self.athena.get_query_results(**kwargs)
                rows = result["ResultSet"]["Rows"]
                if headers is None:
                    headers = [item.get("VarCharValue", "") for item in rows.pop(0)["Data"]]
                for row in rows:
                    values = [item.get("VarCharValue") for item in row.get("Data", [])]
                    values.extend([None] * (len(headers) - len(values)))
                    output.append(dict(zip(headers, values, strict=False)))
                token = result.get("NextToken")
                if not token:
                    return output
        except AthenaTableMissingError:
            raise
        except AthenaTimeoutError:
            raise
        except NoCredentialsError as exc:
            raise S3CredentialsMissingError("AWS credentials are missing for Athena.") from exc
        except EndpointConnectionError as exc:
            raise S3SourceUnavailableError(f"Athena endpoint is unreachable: {exc}") from exc
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code", "")
            if error_code in ("InvalidAccessKeyId", "SignatureDoesNotMatch", "AuthFailure", "AccessDenied", "ExpiredToken"):
                raise S3CredentialsMissingError(f"AWS credentials are invalid for Athena: {exc}") from exc
            raise S3IngestionError(f"Athena Client Error: {exc}") from exc
        except (BotoCoreError, KeyError) as exc:
            raise S3IngestionError(f"Unable to query the CFPB data through Athena: {exc}") from exc

    def _athena_option_values(self, column: str) -> list[str]:
        rows = self._run_athena(
            f"SELECT DISTINCT {column} AS value FROM {self._athena_source} "
            f"WHERE {self._athena_where()} AND {column} IS NOT NULL AND trim(CAST({column} AS varchar)) <> '' "
            "ORDER BY value"
        )
        return [value for row in rows if (value := _text(row.get("value"))) is not None]

    def _load_athena_options(self) -> S3ImportOptionsResponse:
        boundaries = self._run_athena(
            f"SELECT min(date_received) AS min_date, max(date_received) AS max_date "
            f"FROM {self._athena_source} WHERE {self._athena_where()}"
        )
        boundary = boundaries[0] if boundaries else {}
        timely_values = self._athena_option_values("timely_response")
        return S3ImportOptionsResponse(
            source=self.source,
            query_mode="athena",
            products=self._athena_option_values("product"),
            sub_products=self._athena_option_values("sub_product"),
            issues=self._athena_option_values("issue"),
            companies=self._athena_option_values("company"),
            channels=self._athena_option_values("submitted_via"),
            timely_responses=sorted(
                {
                    parsed
                    for value in timely_values
                    if (parsed := _boolean(value)) is not None
                }
            ),
            date_received_min=(
                parsed.date()
                if (parsed := _datetime(boundary.get("min_date"))) is not None
                else None
            ),
            date_received_max=(
                parsed.date()
                if (parsed := _datetime(boundary.get("max_date"))) is not None
                else None
            ),
        )

    def load_options(self) -> S3ImportOptionsResponse:
        if self.query_mode == "athena":
            return self._load_athena_options()
        if hasattr(self, "client"):
            try:
                content_length = self.client.head_object(Bucket=self.bucket, Key=self.key).get(
                    "ContentLength", 0
                )
            except (BotoCoreError, ClientError) as exc:
                raise S3IngestionError(f"Unable to inspect the CFPB object from S3: {exc}") from exc
            if content_length > 250 * 1024 * 1024:
                raise S3QueryModeRequiredError(
                    "Large CFPB CSV filter discovery requires CFPB_INGESTION_MODE=athena."
                )
        scanned = 0
        eligible = 0
        dates: list[date] = []
        timely_responses: set[bool] = set()
        choices: dict[str, set[str]] = {
            "products": set(),
            "sub_products": set(),
            "issues": set(),
            "companies": set(),
            "channels": set(),
        }
        for raw_row in self._rows():
            scanned += 1
            if map_cfpb_csv_row(raw_row) is None:
                continue
            eligible += 1
            if (parsed := _boolean(_value(raw_row, "Timely response?", "timely_response"))) is not None:
                timely_responses.add(parsed)
            if (parsed_date := _datetime(_value(raw_row, "Date received", "date_received"))) is not None:
                dates.append(parsed_date.date())
            for result_field, source_keys in {
                "products": ("Product", "product"),
                "sub_products": ("Sub-product", "sub_product"),
                "issues": ("Issue", "issue"),
                "companies": ("Company", "company"),
                "channels": ("Submitted via", "submitted_via"),
            }.items():
                value = _text(_value(raw_row, *source_keys))
                if value:
                    choices[result_field].add(value)
        return S3ImportOptionsResponse(
            source=self.source,
            query_mode="csv",
            scanned_rows=scanned,
            eligible_rows=eligible,
            timely_responses=sorted(timely_responses),
            date_received_min=min(dates) if dates else None,
            date_received_max=max(dates) if dates else None,
            **{name: sorted(values) for name, values in choices.items()},
        )

    def _athena_selected_rows(self, filters: S3ComplaintImportFilters) -> list[dict[str, Any]]:
        rows = self._run_athena(
            "SELECT complaint_id, consumer_complaint_narrative, product, sub_product, issue, "
            "sub_issue, company, company_response_to_consumer, submitted_via, "
            "CAST(timely_response AS varchar) AS timely_response, "
            "CAST(date_received AS varchar) AS date_received "
            f"FROM {self._athena_source} WHERE {self._athena_where(filters)} "
            f"LIMIT {filters.max_records}"
        )
        return [mapped for row in rows if (mapped := map_cfpb_csv_row(row)) is not None]

    def preview(self, filters: S3ComplaintImportFilters) -> S3ImportPreviewResponse:
        if self.query_mode == "athena":
            rows = self._athena_selected_rows(filters)
            return S3ImportPreviewResponse(
                source=self.source,
                query_mode="athena",
                scanned_rows=0,
                matched_rows=len(rows),
                selected_rows=len(rows),
                result_limited=len(rows) >= filters.max_records,
                items=[
                    S3ComplaintPreviewItem(
                        complaint_id=row["source_complaint_id"],
                        narrative=row["narrative"],
                        product=row["product"],
                        sub_product=row["sub_product"],
                        issue=row["issue"],
                        company=row["company"],
                        channel=row["channel"],
                        timely_response=row["timely_response"],
                        date_received=row["date_received"],
                    )
                    for row in rows
                ],
            )
        scanned = 0
        matched = 0
        selected: list[S3ComplaintPreviewItem] = []
        for raw_row in self._rows():
            scanned += 1
            mapped = map_cfpb_csv_row(raw_row)
            if mapped is None or not _matches(raw_row, filters):
                continue
            matched += 1
            selected.append(
                S3ComplaintPreviewItem(
                    complaint_id=mapped["source_complaint_id"],
                    narrative=mapped["narrative"],
                    product=mapped["product"],
                    sub_product=mapped["sub_product"],
                    issue=mapped["issue"],
                    company=mapped["company"],
                    channel=mapped["channel"],
                    timely_response=mapped["timely_response"],
                    date_received=mapped["date_received"],
                )
            )
            if len(selected) >= filters.max_records:
                break
        return S3ImportPreviewResponse(
            source=self.source,
            query_mode="csv",
            scanned_rows=scanned,
            matched_rows=matched,
            selected_rows=len(selected),
            result_limited=len(selected) >= filters.max_records,
            items=selected,
        )

    def select_rows_for_import(
        self, filters: S3ComplaintImportFilters
    ) -> tuple[int, int, int, list[dict[str, Any]]]:
        if self.query_mode == "athena":
            rows = self._athena_selected_rows(filters)
            return 0, len(rows), 0, rows
        scanned = 0
        matched = 0
        skipped = 0
        selected: dict[str, dict[str, Any]] = {}
        for raw_row in self._rows():
            scanned += 1
            if not _matches(raw_row, filters):
                continue
            mapped = map_cfpb_csv_row(raw_row)
            if mapped is None:
                skipped += 1
                continue
            matched += 1
            selected[mapped["source_complaint_id"]] = mapped
            if len(selected) >= filters.max_records:
                break
        return scanned, matched, skipped, list(selected.values())

    async def import_rows(
        self,
        db: AsyncSession,
        filters: S3ComplaintImportFilters,
        selection: tuple[int, int, int, list[dict[str, Any]]],
    ) -> S3ImportResponse:
        scanned, matched, skipped, rows = selection
        logs = [
            S3ImportLog(level="info", message="Read configured private CFPB import source."),
            S3ImportLog(level="info", message=f"Selected {len(rows)} matching complaint rows."),
        ]
        imported = 0
        for start in range(0, len(rows), 1000):
            batch = rows[start : start + 1000]
            stmt = insert(Complaint).values(batch)
            await db.execute(
                stmt.on_conflict_do_update(
                    index_elements=[Complaint.source_complaint_id],
                    set_={
                        "narrative": stmt.excluded.narrative,
                        "channel": stmt.excluded.channel,
                        "product": stmt.excluded.product,
                        "sub_product": stmt.excluded.sub_product,
                        "issue": stmt.excluded.issue,
                        "sub_issue": stmt.excluded.sub_issue,
                        "company": stmt.excluded.company,
                        "company_response": stmt.excluded.company_response,
                        "timely_response": stmt.excluded.timely_response,
                        "date_received": stmt.excluded.date_received,
                        "updated_at": func.now(),
                    },
                )
            )
            imported += len(batch)
        await db.commit()
        logs.append(S3ImportLog(level="success", message=f"Saved {imported} complaints to PostgreSQL."))
        return S3ImportResponse(
            status="success",
            source=self.source,
            scanned_rows=scanned,
            matched_rows=matched,
            imported_rows=imported,
            skipped_rows=skipped,
            logs=logs,
        )
