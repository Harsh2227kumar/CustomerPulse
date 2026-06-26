import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.core.constants import ChurnRisk, Sentiment
from app.db.session import get_db_session
from app.main import app
from app.models.complaint import Complaint
from app.schemas.ai_response import AIEnrichment, ConfidenceScores
from app.schemas.complaint import ComplaintFilters, ComplaintProcessRequest
from app.services.complaint_service import ComplaintService
from app.services.processing_service import ProcessingService


def sample_enrichment() -> AIEnrichment:
    return AIEnrichment(
        sentiment=Sentiment.NEGATIVE,
        category="General complaint",
        urgency_score=40,
        churn_risk=ChurnRisk.MEDIUM,
        draft_response="We are looking into this.",
        next_action="Investigate issue.",
        confidence_scores=ConfidenceScores(sentiment=90, category=90, urgency=90),
        ai_confidence=0.9,
        ai_reasoning="Reasoning here.",
    )


class WebIntakeTests(unittest.IsolatedAsyncioTestCase):
    def test_get_complaint_categories_endpoint(self) -> None:
        from fastapi import FastAPI
        from app.api.complaints import router as complaints_router
        
        local_app = FastAPI()
        local_app.include_router(complaints_router)
        client = TestClient(local_app)
        
        response = client.get("/api/complaints/categories")
        self.assertEqual(response.status_code, 200)
        categories = response.json()
        self.assertIn("Billing or fees", categories)
        self.assertIn("Fraud or unauthorized activity", categories)
        self.assertIn("General complaint", categories)

    def test_store_enrichment_category_override(self) -> None:
        service = ProcessingService(AsyncMock())
        complaint = Complaint(id="test-1", narrative="narrative")
        enrichment = sample_enrichment()
        now = datetime.now(timezone.utc)

        # 1. Without manual category in request -> uses enrichment category
        request_no_override = ComplaintProcessRequest(
            complaint_id="test-1", narrative="narrative"
        )
        service._store_enrichment(complaint, enrichment, [0.1] * 384, now, request_no_override)
        self.assertEqual(complaint.category, "General complaint")

        # 2. With manual category in request -> overrides enrichment category
        request_with_override = ComplaintProcessRequest(
            complaint_id="test-1", narrative="narrative", category="Billing or fees"
        )
        service._store_enrichment(complaint, enrichment, [0.1] * 384, now, request_with_override)
        self.assertEqual(complaint.category, "Billing or fees")

    async def test_get_or_create_complaint_maps_extra_fields(self) -> None:
        service = ProcessingService(AsyncMock())
        db = AsyncMock()
        db.execute = AsyncMock(return_value=AsyncMock(scalar_one_or_none=lambda: None))

        request = ComplaintProcessRequest(
            complaint_id="test-2",
            narrative="Some narrative text.",
            channel="email",
            product="Credit card",
            sub_product="Gold Card",
            issue="Unexpected charge",
            sub_issue="Late fee charge",
            company="Capital Bank",
            company_response="Closed with explanation",
            timely_response=True,
            date_received=datetime(2026, 6, 26, 12, 0, tzinfo=timezone.utc),
            category="Billing or fees",
        )

        complaint = await service._get_or_create_complaint(db, request)

        self.assertEqual(complaint.source_complaint_id, "test-2")
        self.assertEqual(complaint.narrative, "Some narrative text.")
        self.assertEqual(complaint.channel, "email")
        self.assertEqual(complaint.product, "Credit card")
        self.assertEqual(complaint.sub_product, "Gold Card")
        self.assertEqual(complaint.issue, "Unexpected charge")
        self.assertEqual(complaint.sub_issue, "Late fee charge")
        self.assertEqual(complaint.company, "Capital Bank")
        self.assertEqual(complaint.company_response, "Closed with explanation")
        self.assertEqual(complaint.timely_response, True)
        self.assertEqual(complaint.date_received, request.date_received)

    def test_complaint_filters_validation_and_fields(self) -> None:
        filters = ComplaintFilters(
            limit=10,
            offset=0,
            category="Card services",
            company="Capital Bank",
            sub_product="Gold Card",
            sub_issue="Late fee charge",
        )
        self.assertEqual(filters.category, "Card services")
        self.assertEqual(filters.company, "Capital Bank")
        self.assertEqual(filters.sub_product, "Gold Card")
        self.assertEqual(filters.sub_issue, "Late fee charge")

    async def test_complaint_service_applies_new_filters(self) -> None:
        service = ComplaintService()
        filters = ComplaintFilters(
            limit=10,
            offset=0,
            category="Card services",
            company="Capital Bank",
            sub_product="Gold Card",
            sub_issue="Late fee charge",
        )
        
        # We build a mock SELECT statement and check if the where clauses are added
        from sqlalchemy import select
        stmt = select(Complaint)
        filtered_stmt = service._apply_filters(stmt, filters)
        
        # Verify statement compilation string contains the where clauses
        stmt_str = str(filtered_stmt.compile())
        self.assertIn("complaints.category =", stmt_str)
        self.assertIn("complaints.company =", stmt_str)
        self.assertIn("complaints.sub_product =", stmt_str)
        self.assertIn("complaints.sub_issue =", stmt_str)


if __name__ == "__main__":
    unittest.main()
