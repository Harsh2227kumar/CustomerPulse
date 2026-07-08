from datetime import UTC, datetime
import os
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost/customerpulse_test")
os.environ.setdefault("BEDROCK_API_KEY", "test-key")

from app.api.jobs import router
from app.core.constants import Role
from app.core.security import Principal, get_current_principal
from app.db.session import get_db_session
from app.schemas.jobs import JobCounts, JobListResponse, ProcessingJobResponse


class JobsRouterTests(unittest.TestCase):
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

    def test_list_jobs_forwards_filters_and_pagination(self) -> None:
        item = ProcessingJobResponse(
            job_id="job-1",
            job_type="embedding_backfill",
            status="queued",
            total_items=2,
            counts=JobCounts(queued=2),
            created_by="admin",
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
            items=[],
        )
        service = SimpleNamespace(
            list_jobs=AsyncMock(
                return_value=JobListResponse(
                    items=[item],
                    total_count=1,
                    limit=25,
                    offset=50,
                )
            ),
            close=lambda: None,
        )

        with patch("app.api.jobs.JobService", return_value=service):
            response = self.client.get(
                "/api/jobs?limit=25&offset=50&job_type=embedding_backfill&status=queued"
            )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["total_count"], 1)
        self.assertEqual(body["items"][0]["job_id"], "job-1")
        kwargs = service.list_jobs.await_args.kwargs
        self.assertEqual(kwargs["limit"], 25)
        self.assertEqual(kwargs["offset"], 50)
        self.assertEqual(kwargs["job_type"], "embedding_backfill")
        self.assertEqual(kwargs["status"], "queued")


if __name__ == "__main__":
    unittest.main()

