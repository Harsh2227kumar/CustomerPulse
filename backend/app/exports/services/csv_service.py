import csv
import io
import logging
from collections.abc import AsyncIterable, AsyncIterator, Iterable
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.compliance.reporting.filters import get_compliance_report_records
from app.compliance.reporting.models import ComplianceReportFilter
from app.compliance.reporting.serialiser import get_export_headers, serialise_records
from app.exports.repositories.export_repository import ExportRepository
from app.exports.schemas.export_schemas import (
    AnalyticsCSVExportQuery,
    ComplaintCSVExportQuery,
    FeedbackCSVExportQuery,
)

logger = logging.getLogger(__name__)


class CSVExportService:
    COMPLAINT_COLUMNS = [
        "complaint_id",
        "narrative",
        "channel",
        "product",
        "sub_product",
        "issue",
        "sub_issue",
        "company",
        "company_response",
        "timely_response",
        "date_received",
        "sentiment",
        "category",
        "urgency_score",
        "churn_risk",
        "draft_response",
        "next_action",
        "ai_confidence",
        "ai_status",
        "processed_at",
        "created_at",
    ]
    ANALYTICS_COLUMNS = [
        "product",
        "channel",
        "sentiment",
        "total_complaints",
        "avg_urgency",
        "timely_rate_pct",
        "high_churn_count",
    ]
    FEEDBACK_COLUMNS = [
        "feedback_id",
        "complaint_id",
        "action_type",
        "original_draft_response",
        "final_response",
        "action_used",
        "human_review_outcome",
        "similar_case_useful",
        "created_at",
    ]
    COMPLIANCE_REPORT_COLUMNS = get_export_headers()

    def __init__(self, repository: ExportRepository | None = None) -> None:
        self.repository = repository or ExportRepository()

    async def stream_complaints_csv(
        self,
        db: AsyncSession,
        filters: ComplaintCSVExportQuery,
    ) -> AsyncIterator[str]:
        logger.info("Streaming complaints CSV export with limit=%s.", filters.limit)
        rows = self.repository.stream_complaints(db, filters)
        async for chunk in self._stream_csv_rows(self.COMPLAINT_COLUMNS, rows):
            yield chunk

    async def stream_feedback_csv(
        self,
        db: AsyncSession,
        filters: FeedbackCSVExportQuery,
    ) -> AsyncIterator[str]:
        logger.info("Streaming feedback CSV export with limit=%s.", filters.limit)
        rows = self.repository.stream_feedback(db, filters)
        async for chunk in self._stream_csv_rows(self.FEEDBACK_COLUMNS, rows):
            yield chunk

    async def stream_analytics_csv(
        self,
        db: AsyncSession,
        filters: AnalyticsCSVExportQuery,
    ) -> AsyncIterator[str]:
        logger.info("Streaming analytics CSV export.")
        rows = await self.repository.get_analytics_export_rows(db, filters)
        async for chunk in self._stream_csv_rows(
            self.ANALYTICS_COLUMNS,
            self._iterate_rows(rows),
        ):
            yield chunk

    async def stream_compliance_report_csv(
        self,
        db: AsyncSession,
        filters: ComplianceReportFilter,
    ) -> AsyncIterator[str]:
        logger.info("Streaming compliance report CSV export.")
        records = await get_compliance_report_records(db, filters)
        rows = serialise_records(records)
        async for chunk in self._stream_csv_rows(
            self.COMPLIANCE_REPORT_COLUMNS,
            self._iterate_rows(rows),
        ):
            yield chunk

    async def _stream_csv_rows(
        self,
        fieldnames: list[str],
        rows: AsyncIterable[dict[str, Any]],
    ) -> AsyncIterator[str]:
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        yield self._flush_buffer(buffer)

        async for row in rows:
            writer.writerow(self._serialize_row(fieldnames, row))
            yield self._flush_buffer(buffer)

    async def _iterate_rows(self, rows: Iterable[dict[str, Any]]) -> AsyncIterator[dict[str, Any]]:
        for row in rows:
            yield row

    def _serialize_row(
        self,
        fieldnames: list[str],
        row: dict[str, Any],
    ) -> dict[str, str]:
        return {field: self._serialize_value(field, row.get(field)) for field in fieldnames}

    def _serialize_value(self, field: str, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, bool):
            return "Yes" if value else "No"
        if field == "timely_response":
            return "Yes" if bool(value) else "No"
        if isinstance(value, datetime):
            return self._format_datetime(value)
        if isinstance(value, float):
            return f"{value:.2f}"
        return str(value)

    def _flush_buffer(self, buffer: io.StringIO) -> str:
        payload = buffer.getvalue()
        buffer.seek(0)
        buffer.truncate(0)
        return payload

    def _format_datetime(self, value: datetime) -> str:
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
