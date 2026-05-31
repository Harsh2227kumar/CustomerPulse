from datetime import UTC, datetime
import os
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost/customerpulse_test")
os.environ.setdefault("BEDROCK_API_KEY", "test-key")

from app.db.session import get_db_session
from app.core.constants import Role
from app.core.security import Principal, get_current_principal
from app.exports.api.routes import router
from app.exports.schemas.export_schemas import ComplaintPDFExportQuery
from app.exports.services.pdf_service import PDFExportService


async def _async_chunks(chunks: list[str]):
    for chunk in chunks:
        yield chunk


class PDFExportServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_pdf_bytes_start_with_pdf_signature(self) -> None:
        repository = SimpleNamespace(
            get_pdf_summary=AsyncMock(
                return_value={
                    "total_complaints": 25,
                    "completed_count": 20,
                    "pending_count": 4,
                    "failed_count": 1,
                    "avg_urgency_score": 67.4,
                    "timely_response_pct": 82.5,
                    "high_churn_risk_count": 6,
                }
            ),
            get_sentiment_distribution=AsyncMock(
                return_value=[
                    {"sentiment": "Positive", "count": 3, "percentage": 15.0},
                    {"sentiment": "Neutral", "count": 7, "percentage": 35.0},
                    {"sentiment": "Negative", "count": 10, "percentage": 50.0},
                ]
            ),
            get_top_products=AsyncMock(
                return_value=[
                    {
                        "product": "Credit card",
                        "count": 9,
                        "timely_rate_pct": 88.0,
                        "avg_urgency": 71.0,
                    }
                ]
            ),
            get_top_channels=AsyncMock(
                return_value=[
                    {"channel": "Web", "count": 12, "timely_rate_pct": 81.0}
                ]
            ),
            get_urgency_distribution=AsyncMock(
                return_value=[
                    {"bucket": "Low", "count": 2},
                    {"bucket": "Medium", "count": 4},
                    {"bucket": "High", "count": 8},
                    {"bucket": "Critical", "count": 6},
                ]
            ),
            get_churn_risk_summary=AsyncMock(
                return_value=[
                    {"churn_risk": "Low", "count": 5},
                    {"churn_risk": "Medium", "count": 9},
                    {"churn_risk": "High", "count": 6},
                ]
            ),
        )

        payload = await PDFExportService(repository).build_complaints_report_pdf(
            db=object(),
            filters=ComplaintPDFExportQuery(
                date_from=datetime(2026, 1, 1, tzinfo=UTC),
                date_to=datetime(2026, 1, 31, tzinfo=UTC),
            ),
        )

        self.assertTrue(payload.startswith(b"%PDF-"))


class ExportRouterTests(unittest.TestCase):
    def setUp(self) -> None:
        app = FastAPI()
        app.include_router(router)

        async def override_get_db_session():
            yield object()

        app.dependency_overrides[get_db_session] = override_get_db_session
        app.dependency_overrides[get_current_principal] = lambda: Principal(
            actor="test-manager",
            role=Role.MANAGER,
        )
        self.client = TestClient(app)

    def test_complaints_csv_streams_with_attachment_headers(self) -> None:
        service = SimpleNamespace(
            stream_complaints_csv=lambda db, filters: _async_chunks(
                [
                    "complaint_id,narrative\n",
                    "SRC-1,Unexpected fee\n",
                ]
            )
        )

        with patch("app.exports.api.routes.CSVExportService", return_value=service):
            response = self.client.get("/api/exports/complaints/csv")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.headers["content-type"].startswith("text/csv"))
        self.assertIn("attachment;", response.headers["content-disposition"])
        self.assertIn("complaints_", response.headers["content-disposition"])
        self.assertIn("SRC-1", response.text)

    def test_complaints_pdf_sets_pdf_headers_and_signature(self) -> None:
        service = SimpleNamespace(
            build_complaints_report_pdf=AsyncMock(return_value=b"%PDF-1.7\nmock-pdf")
        )

        with patch("app.exports.api.routes.PDFExportService", return_value=service):
            response = self.client.get("/api/exports/complaints/pdf")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.headers["content-type"].startswith("application/pdf"))
        self.assertIn("CustomerPulse_Report_", response.headers["content-disposition"])
        self.assertTrue(response.content.startswith(b"%PDF-"))

    def test_feedback_csv_invalid_action_type_returns_422(self) -> None:
        response = self.client.get("/api/exports/feedback/csv?action_type=bad-value")
        self.assertEqual(response.status_code, 422)

    def test_analytics_csv_streams(self) -> None:
        service = SimpleNamespace(
            stream_analytics_csv=lambda db, filters: _async_chunks(
                [
                    "product,channel,sentiment,total_complaints,avg_urgency,timely_rate_pct,high_churn_count\n",
                    "Credit card,Web,Negative,8,72.50,75.00,3\n",
                ]
            )
        )

        with patch("app.exports.api.routes.CSVExportService", return_value=service):
            response = self.client.get("/api/exports/analytics/csv")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.headers["content-type"].startswith("text/csv"))
        self.assertIn("Credit card", response.text)


if __name__ == "__main__":
    unittest.main()
