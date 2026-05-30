import csv
import io
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from httpx import ASGITransport, AsyncClient

from app.db.session import get_db_session
from app.main import app
from app.exports.repositories.export_repository import ExportRepository
from app.exports.schemas.export_schemas import AnalyticsCSVExportQuery, ComplaintCSVExportQuery, FeedbackCSVExportQuery
from app.exports.services.csv_service import CSVExportService
from backend.tests.conftest import FakeAsyncDB, collect_async_text, complaint_row


class CSVExportServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_csv_contains_all_required_columns(self) -> None:
        service = CSVExportService(
            SimpleNamespace(stream_complaints=lambda db, filters: _rows([complaint_row()]))
        )

        payload = await collect_async_text(
            service.stream_complaints_csv(object(), ComplaintCSVExportQuery())
        )

        self.assertEqual(next(csv.reader(io.StringIO(payload))), CSVExportService.COMPLAINT_COLUMNS)

    async def test_csv_none_values_serialize_as_empty_string(self) -> None:
        row = complaint_row(sub_product=None, sub_issue=None, processed_at=None, company_response=None)
        service = CSVExportService(
            SimpleNamespace(stream_complaints=lambda db, filters: _rows([row]))
        )

        payload = await collect_async_text(
            service.stream_complaints_csv(object(), ComplaintCSVExportQuery())
        )

        parsed = list(csv.DictReader(io.StringIO(payload)))[0]
        self.assertEqual(parsed["sub_product"], "")
        self.assertEqual(parsed["sub_issue"], "")
        self.assertEqual(parsed["company_response"], "")
        self.assertEqual(parsed["processed_at"], "")

    async def test_csv_timely_response_true_serializes_as_yes(self) -> None:
        service = CSVExportService(
            SimpleNamespace(stream_complaints=lambda db, filters: _rows([complaint_row(timely_response=True)]))
        )

        payload = await collect_async_text(service.stream_complaints_csv(object(), ComplaintCSVExportQuery()))
        self.assertEqual(list(csv.DictReader(io.StringIO(payload)))[0]["timely_response"], "Yes")

    async def test_csv_timely_response_false_serializes_as_no(self) -> None:
        service = CSVExportService(
            SimpleNamespace(stream_complaints=lambda db, filters: _rows([complaint_row(timely_response=False)]))
        )

        payload = await collect_async_text(service.stream_complaints_csv(object(), ComplaintCSVExportQuery()))
        self.assertEqual(list(csv.DictReader(io.StringIO(payload)))[0]["timely_response"], "No")

    async def test_csv_timely_response_none_serializes_as_empty(self) -> None:
        service = CSVExportService(
            SimpleNamespace(stream_complaints=lambda db, filters: _rows([complaint_row(timely_response=None)]))
        )

        payload = await collect_async_text(service.stream_complaints_csv(object(), ComplaintCSVExportQuery()))
        self.assertEqual(list(csv.DictReader(io.StringIO(payload)))[0]["timely_response"], "")

    async def test_csv_datetime_uses_iso8601_format(self) -> None:
        service = CSVExportService(
            SimpleNamespace(stream_complaints=lambda db, filters: _rows([complaint_row()]))
        )

        payload = await collect_async_text(service.stream_complaints_csv(object(), ComplaintCSVExportQuery()))
        parsed = list(csv.DictReader(io.StringIO(payload)))[0]

        self.assertEqual(parsed["date_received"], "2026-01-15T00:00:00Z")
        self.assertEqual(parsed["processed_at"], "2026-01-15T10:30:00Z")

    async def test_csv_respects_limit_cap_5000(self) -> None:
        repository = ExportRepository()
        fake_db = FakeAsyncDB()

        async for _ in repository.stream_complaints(
            fake_db,
            ComplaintCSVExportQuery(limit=5000),
        ):
            pass

        self.assertEqual(fake_db.statements[0]._limit_clause.value, 5000)

    async def test_analytics_csv_contains_correct_aggregation_columns(self) -> None:
        service = CSVExportService(
            SimpleNamespace(
                get_analytics_export_rows=AsyncMock(
                    return_value=[
                        {
                            "product": "Credit card",
                            "channel": "Web",
                            "sentiment": "Negative",
                            "total_complaints": 7,
                            "avg_urgency": 72.5,
                            "timely_rate_pct": 75.0,
                            "high_churn_count": 3,
                        }
                    ]
                )
            )
        )

        payload = await collect_async_text(
            service.stream_analytics_csv(object(), AnalyticsCSVExportQuery())
        )

        self.assertEqual(next(csv.reader(io.StringIO(payload))), CSVExportService.ANALYTICS_COLUMNS)

    async def test_feedback_csv_contains_all_retraining_columns(self) -> None:
        service = CSVExportService(
            SimpleNamespace(
                stream_feedback=lambda db, filters: _rows(
                    [
                        {
                            "feedback_id": "fb-1",
                            "complaint_id": "CP-001",
                            "action_type": "accepted",
                            "original_draft_response": "Draft",
                            "final_response": "Final",
                            "action_used": True,
                            "human_review_outcome": "resolved",
                            "similar_case_useful": True,
                            "created_at": datetime(2026, 1, 15, 11, 0, tzinfo=timezone.utc),
                        }
                    ]
                )
            )
        )

        payload = await collect_async_text(
            service.stream_feedback_csv(object(), FeedbackCSVExportQuery())
        )

        self.assertEqual(next(csv.reader(io.StringIO(payload))), CSVExportService.FEEDBACK_COLUMNS)


async def _rows(rows):
    for row in rows:
        yield row


async def _chunks(chunks):
    for chunk in chunks:
        yield chunk


class CSVExportEndpointTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        async def override_get_db_session():
            yield object()

        app.dependency_overrides[get_db_session] = override_get_db_session

    async def asyncTearDown(self) -> None:
        app.dependency_overrides.clear()

    async def test_export_complaints_csv_returns_200(self) -> None:
        service = SimpleNamespace(
            stream_complaints_csv=lambda db, filters: _chunks(
                ["complaint_id,narrative\n", "CP-001,My credit card was charged incorrectly.\n"]
            )
        )
        with patch("app.exports.api.routes.CSVExportService", return_value=service):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/api/exports/complaints/csv")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.headers["content-type"].startswith("text/csv"))

    async def test_export_analytics_csv_returns_200(self) -> None:
        service = SimpleNamespace(
            stream_analytics_csv=lambda db, filters: _chunks(
                [
                    "product,channel,sentiment,total_complaints,avg_urgency,timely_rate_pct,high_churn_count\n",
                    "Credit card,Web,Negative,8,72.50,75.00,3\n",
                ]
            )
        )
        with patch("app.exports.api.routes.CSVExportService", return_value=service):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/api/exports/analytics/csv")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.headers["content-type"].startswith("text/csv"))

    async def test_export_feedback_csv_returns_200(self) -> None:
        service = SimpleNamespace(
            stream_feedback_csv=lambda db, filters: _chunks(
                [
                    "feedback_id,complaint_id,action_type,original_draft_response,final_response,action_used,human_review_outcome,similar_case_useful,created_at\n",
                    "fb-1,CP-001,accepted,Draft,Final,Yes,resolved,Yes,2026-01-15T11:00:00Z\n",
                ]
            )
        )
        with patch("app.exports.api.routes.CSVExportService", return_value=service):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/api/exports/feedback/csv")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.headers["content-type"].startswith("text/csv"))

    async def test_export_csv_validation_errors_return_422(self) -> None:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            complaints = await client.get("/api/exports/complaints/csv", params={"limit": 5001})
            feedback = await client.get("/api/exports/feedback/csv", params={"action_type": "bad-value"})

        self.assertEqual(complaints.status_code, 422)
        self.assertEqual(feedback.status_code, 422)
