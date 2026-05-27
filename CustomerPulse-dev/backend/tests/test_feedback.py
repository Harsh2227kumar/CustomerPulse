from datetime import UTC, datetime
import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost/customerpulse_test")
os.environ.setdefault("BEDROCK_API_KEY", "test-key")

from app.db.session import get_db_session
from app.feedback.router import router
from app.feedback.schemas import (
    AgentFeedbackUpsertRequest,
    FeedbackListQuery,
    FeedbackListResponse,
    FeedbackRead,
)
from app.feedback.service import ComplaintNotFoundError, FeedbackNotFoundError, FeedbackService


class FeedbackServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_insert_feedback_returns_created(self) -> None:
        complaint = SimpleNamespace(id="pk-1", source_complaint_id="SRC-1")
        feedback = SimpleNamespace(
            agent_id="agent-1",
            feedback_action="accepted",
            final_response="Approved reply",
            action_used=True,
            human_review_outcome="resolved",
            similar_cases_useful=True,
            notes="Looks good",
            revision_count=0,
            submitted_at=datetime(2026, 1, 1, tzinfo=UTC),
            updated_at=datetime(2026, 1, 1, tzinfo=UTC),
        )
        repository = SimpleNamespace(
            get_complaint_by_source_id=AsyncMock(return_value=complaint),
            feedback_exists=AsyncMock(return_value=False),
            upsert_feedback=AsyncMock(return_value=feedback),
        )

        result, created = await FeedbackService(repository).upsert_feedback(
            db=object(),
            complaint_id="SRC-1",
            payload=AgentFeedbackUpsertRequest(
                agent_id="agent-1",
                feedback_action="accepted",
                final_response="Approved reply",
                action_used=True,
                human_review_outcome="resolved",
                similar_cases_useful=True,
                notes="Looks good",
            ),
        )

        self.assertTrue(created)
        self.assertEqual(result.complaint_id, "SRC-1")
        self.assertEqual(result.revision_count, 0)

    async def test_duplicate_submission_increments_revision_count(self) -> None:
        complaint = SimpleNamespace(id="pk-1", source_complaint_id="SRC-1")
        feedback = SimpleNamespace(
            agent_id="agent-1",
            feedback_action="edited",
            final_response="Edited reply",
            action_used=False,
            human_review_outcome="pending",
            similar_cases_useful=None,
            notes=None,
            revision_count=1,
            submitted_at=datetime(2026, 1, 1, tzinfo=UTC),
            updated_at=datetime(2026, 1, 2, tzinfo=UTC),
        )
        repository = SimpleNamespace(
            get_complaint_by_source_id=AsyncMock(return_value=complaint),
            feedback_exists=AsyncMock(return_value=True),
            upsert_feedback=AsyncMock(return_value=feedback),
        )

        result, created = await FeedbackService(repository).upsert_feedback(
            db=object(),
            complaint_id="SRC-1",
            payload=AgentFeedbackUpsertRequest(
                agent_id="agent-1",
                feedback_action="edited",
                final_response="Edited reply",
                action_used=False,
                human_review_outcome="pending",
            ),
        )

        self.assertFalse(created)
        self.assertEqual(result.revision_count, 1)

    async def test_complaint_not_found_raises_error(self) -> None:
        repository = SimpleNamespace(
            get_complaint_by_source_id=AsyncMock(return_value=None),
        )

        with self.assertRaises(ComplaintNotFoundError):
            await FeedbackService(repository).upsert_feedback(
                db=object(),
                complaint_id="missing",
                payload=AgentFeedbackUpsertRequest(
                    agent_id="agent-1",
                    feedback_action="accepted",
                    human_review_outcome="resolved",
                ),
            )


class FeedbackRouterTests(unittest.TestCase):
    def setUp(self) -> None:
        app = FastAPI()
        app.include_router(router)

        async def override_get_db_session():
            yield object()

        app.dependency_overrides[get_db_session] = override_get_db_session
        self.client = TestClient(app)

    def test_invalid_feedback_action_returns_422(self) -> None:
        response = self.client.post(
            "/api/feedback/SRC-1",
            json={
                "agent_id": "agent-1",
                "feedback_action": "bad-value",
                "human_review_outcome": "resolved",
            },
        )

        self.assertEqual(response.status_code, 422)

    def test_blank_agent_id_returns_422(self) -> None:
        response = self.client.post(
            "/api/feedback/SRC-1",
            json={
                "agent_id": "   ",
                "feedback_action": "accepted",
                "human_review_outcome": "resolved",
            },
        )

        self.assertEqual(response.status_code, 422)

    def test_get_feedback(self) -> None:
        item = FeedbackRead(
            complaint_id="SRC-1",
            agent_id="agent-1",
            feedback_action="accepted",
            final_response="Approved reply",
            action_used=True,
            human_review_outcome="resolved",
            similar_cases_useful=True,
            notes="done",
            revision_count=0,
            submitted_at=datetime(2026, 1, 1, tzinfo=UTC),
            updated_at=datetime(2026, 1, 1, tzinfo=UTC),
        )
        service = SimpleNamespace(get_feedback=AsyncMock(return_value=item))

        with patch("app.feedback.router.FeedbackService", return_value=service):
            response = self.client.get("/api/feedback/SRC-1")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["complaint_id"], "SRC-1")

    def test_list_feedback(self) -> None:
        item = FeedbackRead(
            complaint_id="SRC-1",
            agent_id="agent-1",
            feedback_action="accepted",
            final_response=None,
            action_used=None,
            human_review_outcome="resolved",
            similar_cases_useful=None,
            notes=None,
            revision_count=0,
            submitted_at=datetime(2026, 1, 1, tzinfo=UTC),
            updated_at=datetime(2026, 1, 1, tzinfo=UTC),
        )
        service = SimpleNamespace(
            list_feedback=AsyncMock(
                return_value=FeedbackListResponse(
                    items=[item],
                    limit=50,
                    offset=0,
                    count=1,
                )
            )
        )

        with patch("app.feedback.router.FeedbackService", return_value=service):
            response = self.client.get("/api/feedback")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["count"], 1)
        self.assertEqual(body["items"][0]["complaint_id"], "SRC-1")
        args = service.list_feedback.await_args.args
        self.assertIsInstance(args[1], FeedbackListQuery)

    def test_export_ndjson_endpoint(self) -> None:
        items = [
            FeedbackRead(
                complaint_id="SRC-1",
                agent_id="agent-1",
                feedback_action="accepted",
                final_response="Approved reply",
                action_used=True,
                human_review_outcome="resolved",
                similar_cases_useful=True,
                notes=None,
                revision_count=0,
                submitted_at=datetime(2026, 1, 1, tzinfo=UTC),
                updated_at=datetime(2026, 1, 1, tzinfo=UTC),
            )
        ]
        service = SimpleNamespace(export_feedback=AsyncMock(return_value=items))

        with patch("app.feedback.router.FeedbackService", return_value=service):
            response = self.client.get("/api/feedback/export")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.headers["content-type"].startswith("application/x-ndjson"))
        lines = [line for line in response.text.splitlines() if line]
        self.assertEqual(len(lines), 1)
        self.assertEqual(json.loads(lines[0])["complaint_id"], "SRC-1")

    def test_get_feedback_not_found(self) -> None:
        service = SimpleNamespace(get_feedback=AsyncMock(side_effect=FeedbackNotFoundError("missing")))

        with patch("app.feedback.router.FeedbackService", return_value=service):
            response = self.client.get("/api/feedback/missing")

        self.assertEqual(response.status_code, 404)
