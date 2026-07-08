import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from httpx import ASGITransport, AsyncClient

from app.core.constants import Role
from app.core.security import Principal, get_current_principal
from app.db.session import get_db_session
from app.exports.repositories.export_repository import ExportRepository
from app.exports.schemas.export_schemas import FeedbackCSVExportQuery
from app.feedback.schemas import AgentFeedbackUpsertRequest
from app.feedback.service import FeedbackService
from app.main import app
from tests.conftest import FakeAsyncDB, feedback_payload, feedback_record, make_async_repository


class FeedbackTests(unittest.IsolatedAsyncioTestCase):
    async def test_feedback_accepted_persists_correctly(self) -> None:
        complaint = SimpleNamespace(id="pk-1", source_complaint_id="CP-001")
        repository = make_async_repository(
            get_complaint_by_source_id=complaint,
            feedback_exists=False,
            upsert_feedback=feedback_record(feedback_action="accepted"),
        )

        result, created = await FeedbackService(repository).upsert_feedback(
            object(),
            "CP-001",
            AgentFeedbackUpsertRequest(**feedback_payload(feedback_action="accepted")),
        )

        self.assertTrue(created)
        self.assertEqual(result.feedback_action, "accepted")

    async def test_feedback_edited_captures_final_response(self) -> None:
        complaint = SimpleNamespace(id="pk-1", source_complaint_id="CP-001")
        repository = make_async_repository(
            get_complaint_by_source_id=complaint,
            feedback_exists=True,
            upsert_feedback=feedback_record(feedback_action="edited", final_response="Final agent-approved response.", revision_count=1),
        )

        result, created = await FeedbackService(repository).upsert_feedback(
            object(),
            "CP-001",
            AgentFeedbackUpsertRequest(**feedback_payload(feedback_action="edited", final_response="Final agent-approved response.")),
        )

        self.assertFalse(created)
        self.assertEqual(result.final_response, "Final agent-approved response.")

    async def test_feedback_rejected_records_outcome(self) -> None:
        complaint = SimpleNamespace(id="pk-1", source_complaint_id="CP-001")
        repository = make_async_repository(
            get_complaint_by_source_id=complaint,
            feedback_exists=False,
            upsert_feedback=feedback_record(feedback_action="rejected", human_review_outcome="closed"),
        )

        result, _ = await FeedbackService(repository).upsert_feedback(
            object(),
            "CP-001",
            AgentFeedbackUpsertRequest(**feedback_payload(feedback_action="rejected", human_review_outcome="closed", action_used=False)),
        )

        self.assertEqual(result.feedback_action, "rejected")
        self.assertEqual(result.human_review_outcome, "closed")

    async def test_feedback_escalated_sets_human_review(self) -> None:
        complaint = SimpleNamespace(id="pk-1", source_complaint_id="CP-001")
        repository = make_async_repository(
            get_complaint_by_source_id=complaint,
            feedback_exists=False,
            upsert_feedback=feedback_record(feedback_action="escalated", human_review_outcome="escalated_tier2"),
        )

        result, _ = await FeedbackService(repository).upsert_feedback(
            object(),
            "CP-001",
            AgentFeedbackUpsertRequest(
                **feedback_payload(feedback_action="escalated", human_review_outcome="escalated_tier2")
            ),
        )

        self.assertEqual(result.human_review_outcome, "escalated_tier2")

    async def test_feedback_export_query_filters_by_action_type(self) -> None:
        repository = ExportRepository()
        fake_db = FakeAsyncDB()

        async for _ in repository.stream_feedback(
            fake_db,
            FeedbackCSVExportQuery(action_type="accepted"),
        ):
            pass

        self.assertIn("feedback_action", str(fake_db.statements[0]))

    async def test_feedback_export_query_filters_by_date_range(self) -> None:
        repository = ExportRepository()
        fake_db = FakeAsyncDB()

        async for _ in repository.stream_feedback(
            fake_db,
            FeedbackCSVExportQuery(
                date_from=datetime(2026, 1, 1, tzinfo=timezone.utc),
                date_to=datetime(2026, 1, 31, tzinfo=timezone.utc),
            ),
        ):
            pass

        statement = str(fake_db.statements[0])
        self.assertIn("submitted_at", statement)

    async def test_similar_case_usefulness_flag_stored(self) -> None:
        complaint = SimpleNamespace(id="pk-1", source_complaint_id="CP-001")
        repository = make_async_repository(
            get_complaint_by_source_id=complaint,
            feedback_exists=False,
            upsert_feedback=feedback_record(similar_cases_useful=True),
        )

        result, _ = await FeedbackService(repository).upsert_feedback(
            object(),
            "CP-001",
            AgentFeedbackUpsertRequest(**feedback_payload(similar_cases_useful=True)),
        )

        self.assertTrue(result.similar_cases_useful)


class FeedbackEndpointTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        async def override_get_db_session():
            yield object()

        app.dependency_overrides[get_db_session] = override_get_db_session
        app.dependency_overrides[get_current_principal] = lambda: Principal(
            actor="test-agent",
            role=Role.AGENT,
        )

    async def asyncTearDown(self) -> None:
        app.dependency_overrides.clear()

    async def test_feedback_endpoint_is_async(self) -> None:
        payload = SimpleNamespace(
            upsert_feedback=AsyncMock(
                return_value=(
                    {
                        "complaint_id": "CP-001",
                        "agent_id": "agent-007",
                        "feedback_action": "accepted",
                        "final_response": "Approved",
                        "action_used": True,
                        "human_review_outcome": "resolved",
                        "similar_cases_useful": True,
                        "notes": None,
                        "revision_count": 0,
                        "submitted_at": "2026-01-15T11:00:00Z",
                        "updated_at": "2026-01-15T11:00:00Z",
                    },
                    True,
                )
            )
        )
        with patch("app.feedback.router.FeedbackService", return_value=payload):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post("/api/feedback/CP-001", json=feedback_payload())

        self.assertEqual(response.status_code, 201)

    async def test_feedback_validation_returns_422(self) -> None:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/feedback/CP-001",
                json=feedback_payload(feedback_action="invalid"),
            )

        self.assertEqual(response.status_code, 422)
