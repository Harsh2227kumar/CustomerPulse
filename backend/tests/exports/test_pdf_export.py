import io
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

from httpx import ASGITransport, AsyncClient
from reportlab.platypus import Paragraph, Table

from app.db.session import get_db_session
from app.main import app
from app.exports.schemas.export_schemas import ComplaintPDFExportQuery
from app.exports.services.pdf_service import PDFExportService


def _pdf_repository():
    return SimpleNamespace(
        get_pdf_summary=unittest.mock.AsyncMock(
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
        get_sentiment_distribution=unittest.mock.AsyncMock(
            return_value=[
                {"sentiment": "Positive", "count": 3, "percentage": 15.0},
                {"sentiment": "Neutral", "count": 7, "percentage": 35.0},
                {"sentiment": "Negative", "count": 10, "percentage": 50.0},
            ]
        ),
        get_top_products=unittest.mock.AsyncMock(
            return_value=[
                {"product": "Credit card", "count": 9, "timely_rate_pct": 88.0, "avg_urgency": 71.0}
            ]
        ),
        get_top_channels=unittest.mock.AsyncMock(
            return_value=[{"channel": "Web", "count": 12, "timely_rate_pct": 81.0}]
        ),
        get_urgency_distribution=unittest.mock.AsyncMock(
            return_value=[
                {"bucket": "Low", "count": 2},
                {"bucket": "Medium", "count": 4},
                {"bucket": "High", "count": 8},
                {"bucket": "Critical", "count": 6},
            ]
        ),
        get_churn_risk_summary=unittest.mock.AsyncMock(
            return_value=[
                {"churn_risk": "Low", "count": 5},
                {"churn_risk": "Medium", "count": 9},
                {"churn_risk": "High", "count": 6},
            ]
        ),
    )


class PDFExportServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_pdf_generates_non_empty_bytes(self) -> None:
        payload = await PDFExportService(_pdf_repository()).build_complaints_report_pdf(
            object(),
            ComplaintPDFExportQuery(),
        )

        self.assertGreater(len(payload), 0)

    async def test_pdf_is_valid_pdf_magic_bytes(self) -> None:
        payload = await PDFExportService(_pdf_repository()).build_complaints_report_pdf(
            object(),
            ComplaintPDFExportQuery(),
        )

        self.assertTrue(payload.startswith(b"%PDF-"))

    async def test_pdf_generation_uses_bytesio_not_filesystem(self) -> None:
        service = PDFExportService(_pdf_repository())
        with patch("app.exports.services.pdf_service.io.BytesIO", wraps=io.BytesIO) as bytesio:
            await service.build_complaints_report_pdf(object(), ComplaintPDFExportQuery())

        self.assertTrue(bytesio.called)

    async def test_pdf_cover_page_includes_title(self) -> None:
        service = PDFExportService(_pdf_repository())

        cover = service._build_cover_page(
            ComplaintPDFExportQuery(),
            datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc),
        )

        title = next(item for item in cover if isinstance(item, Paragraph))
        self.assertIn("CustomerPulse AI", title.getPlainText())

    async def test_pdf_executive_summary_uses_real_data(self) -> None:
        service = PDFExportService(_pdf_repository())

        section = service._build_executive_summary(
            {
                "total_complaints": 11,
                "completed_count": 9,
                "pending_count": 1,
                "failed_count": 1,
                "avg_urgency_score": 73.25,
                "timely_response_pct": 81.81,
                "high_churn_risk_count": 4,
            }
        )

        table = next(item for item in section if isinstance(item, Table))
        flattened = [cell for row in table._cellvalues for cell in row]
        self.assertIn("11", flattened)
        self.assertIn("81.81%", flattened)

    async def test_pdf_handles_zero_complaints_gracefully(self) -> None:
        repository = _pdf_repository()
        repository.get_pdf_summary.return_value = {
            "total_complaints": 0,
            "completed_count": 0,
            "pending_count": 0,
            "failed_count": 0,
            "avg_urgency_score": 0,
            "timely_response_pct": 0,
            "high_churn_risk_count": 0,
        }
        payload = await PDFExportService(repository).build_complaints_report_pdf(
            object(),
            ComplaintPDFExportQuery(),
        )

        self.assertTrue(payload.startswith(b"%PDF-"))

    async def test_pdf_all_sections_present_in_output(self) -> None:
        service = PDFExportService(_pdf_repository())
        story = service._build_story(
            {
                "summary": {"total_complaints": 1, "completed_count": 1, "pending_count": 0, "failed_count": 0, "avg_urgency_score": 50, "timely_response_pct": 100, "high_churn_risk_count": 0},
                "sentiment_distribution": [{"sentiment": "Positive", "count": 1, "percentage": 100.0}],
                "top_products": [{"product": "Credit card", "count": 1, "timely_rate_pct": 100.0, "avg_urgency": 50.0}],
                "top_channels": [{"channel": "Web", "count": 1, "timely_rate_pct": 100.0}],
                "urgency_distribution": [{"bucket": "Low", "count": 1}],
                "churn_risk_summary": [{"churn_risk": "Low", "count": 1}],
            },
            ComplaintPDFExportQuery(),
            datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc),
        )

        text_blocks = [item.getPlainText() for item in story if isinstance(item, Paragraph)]
        self.assertIn("Executive Summary", text_blocks)
        self.assertIn("Sentiment Distribution", text_blocks)
        self.assertIn("Top 10 Products by Volume", text_blocks)
        self.assertIn("Top 5 Channels", text_blocks)
        self.assertIn("Urgency Distribution", text_blocks)
        self.assertIn("Churn Risk Summary", text_blocks)


class PDFExportEndpointTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        async def override_get_db_session():
            yield object()

        app.dependency_overrides[get_db_session] = override_get_db_session

    async def asyncTearDown(self) -> None:
        app.dependency_overrides.clear()

    async def test_export_complaints_pdf_returns_200(self) -> None:
        service = SimpleNamespace(build_complaints_report_pdf=unittest.mock.AsyncMock(return_value=b"%PDF-1.7\nmock"))
        with patch("app.exports.api.routes.PDFExportService", return_value=service):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/api/exports/complaints/pdf")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.headers["content-type"].startswith("application/pdf"))
        self.assertTrue(response.content.startswith(b"%PDF-"))

    async def test_export_pdf_validation_errors_return_422(self) -> None:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                "/api/exports/complaints/pdf",
                params={"product": "x" * 256},
            )

        self.assertEqual(response.status_code, 422)
