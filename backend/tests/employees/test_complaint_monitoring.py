"""Tests for GET /api/admin/complaint-monitoring.

Covers:
- Endpoint returns combined data matching the underlying services queried directly.
- Manager/agent calling this admin-scoped endpoint gets 403.
- Endpoint is GET-only.
"""
import os
import sys
import unittest
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost/test")
os.environ.setdefault("BEDROCK_API_KEY", "test-key")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.core.constants import Role
from app.core.security import Principal, get_current_principal
from app.db.session import get_db_session

class MonitoringEndpointTests(unittest.TestCase):
    def _build_client(self, role: Role, actor: str = "EMP999"):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from app.employees.router import admin_router

        app = FastAPI()
        app.include_router(admin_router)

        async def _override_db():
            yield object()

        app.dependency_overrides[get_db_session] = _override_db
        app.dependency_overrides[get_current_principal] = lambda: Principal(
            actor=actor, role=role
        )
        return TestClient(app)

    @patch("app.operations.repository.OperationsRepository")
    @patch("app.sla.services.sla_service.SLAService")
    @patch("app.escalations.repository.EscalationRepository")
    def test_admin_monitoring_success(
        self, mock_esc_repo_class, mock_sla_svc_class, mock_ops_repo_class
    ):
        mock_ops_repo = MagicMock()
        mock_ops_repo.get_queue = AsyncMock(return_value=([], 0))
        mock_ops_repo_class.return_value = mock_ops_repo

        mock_sla_svc = MagicMock()
        from app.sla.schemas.sla_schemas import SLASummaryResponse
        mock_sla_svc.get_summary = AsyncMock(
            return_value=SLASummaryResponse(
                total_complaints=100,
                timely_count=90,
                untimely_count=10,
                timely_rate_pct=90.0,
                high_urgency_untimely_count=2,
            )
        )
        mock_sla_svc_class.return_value = mock_sla_svc

        mock_esc_repo = MagicMock()
        mock_esc_repo.count_by_status = AsyncMock(return_value={"open": 5, "resolved": 10})
        mock_esc_repo_class.return_value = mock_esc_repo

        client = self._build_client(Role.ADMIN)
        resp = client.get("/api/admin/complaint-monitoring")
        self.assertEqual(resp.status_code, 200)
        
        data = resp.json()
        self.assertIn("operations_queue", data)
        self.assertIn("sla_summary", data)
        self.assertIn("escalation_counts", data)
        self.assertIn("generated_at", data)
        
        self.assertEqual(data["escalation_counts"]["open"], 5)
        self.assertEqual(data["sla_summary"]["total_complaints"], 100)

    def test_agent_monitoring_forbidden(self):
        client = self._build_client(Role.AGENT)
        resp = client.get("/api/admin/complaint-monitoring")
        self.assertEqual(resp.status_code, 403)

    def test_manager_monitoring_forbidden(self):
        client = self._build_client(Role.MANAGER)
        resp = client.get("/api/admin/complaint-monitoring")
        self.assertEqual(resp.status_code, 403)

    def test_monitoring_is_read_only(self):
        client = self._build_client(Role.ADMIN)
        resp = client.post("/api/admin/complaint-monitoring", json={})
        self.assertEqual(resp.status_code, 405)

if __name__ == "__main__":
    unittest.main()
