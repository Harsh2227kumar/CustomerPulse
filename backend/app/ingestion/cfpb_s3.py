from __future__ import annotations

import csv
import tempfile
import zipfile
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from io import TextIOWrapper
from typing import Any, TextIO

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.constants import ProcessingStatus
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
    return None


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
    return {
        "id": f"cfpb-{complaint_id}"[:64],
        "source_complaint_id": complaint_id,
        "narrative": narrative,
        "channel": _text(_value(row, "Submitted via", "submitted_via"), 64),
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
        self.client = boto3.client("s3", region_name=settings.aws_region)

    @property
    def source(self) -> S3SourceSummary:
        return S3SourceSummary(bucket=self.bucket, key=self.key)

    @contextmanager
    def _csv_stream(self) -> Iterator[TextIO]:
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
        except (BotoCoreError, ClientError, OSError, zipfile.BadZipFile) as exc:
            raise S3IngestionError(f"Unable to read the CFPB object from S3: {exc}") from exc

    def _rows(self) -> Iterator[dict[str, Any]]:
        with self._csv_stream() as stream:
            yield from csv.DictReader(stream)

    def load_options(self) -> S3ImportOptionsResponse:
        scanned = 0
        eligible = 0
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
            scanned_rows=scanned,
            eligible_rows=eligible,
            **{name: sorted(values) for name, values in choices.items()},
        )

    def preview(self, filters: S3ComplaintImportFilters) -> S3ImportPreviewResponse:
        scanned = 0
        matched = 0
        selected: list[S3ComplaintPreviewItem] = []
        for raw_row in self._rows():
            scanned += 1
            mapped = map_cfpb_csv_row(raw_row)
            if mapped is None or not _matches(raw_row, filters):
                continue
            matched += 1
            if len(selected) < filters.max_records:
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
        return S3ImportPreviewResponse(
            source=self.source,
            scanned_rows=scanned,
            matched_rows=matched,
            selected_rows=len(selected),
            items=selected,
        )

    def select_rows_for_import(
        self, filters: S3ComplaintImportFilters
    ) -> tuple[int, int, int, list[dict[str, Any]]]:
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
            S3ImportLog(level="info", message=f"Read S3 object s3://{self.bucket}/{self.key}."),
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
