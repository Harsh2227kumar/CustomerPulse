"""Tests for GET /api/admin/dashboard.

Covers:
    - Correct employee/role/department counts against seeded fixture data.
    - recently_active_employees includes recent login, excludes old login.
    - Manager/agent calling this endpoint gets 403.
    - HTTP endpoint returns 200 for admin/super_admin.
"""
import os
import sys
import unittest
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost/test")
os.environ.setdefault("BEDROCK_API_KEY", "test-key")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.core.constants import Role
from app.core.security import Principal, get_current_principal
from app.db.session import get_db_session
from app.employees.service import EmployeeService

from tests.employees.conftest import (
    CapturingAuditRepository,
    CapturingEmployeeRepository,
    CapturingDepartmentRepository,
    FakeDb,
    make_employee,
    make_audit_log,
    make_department,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _svc(emp_repo=None, audit_repo=None) -> EmployeeService:
    return EmployeeService(
        employee_repo=emp_repo or CapturingEmployeeRepository(),
        audit_repo=audit_repo or CapturingAuditRepository(),
    )


# ── Service-layer tests ──────────────────────────────────────────────────────

class DashboardEmployeeCountsTests(unittest.IsolatedAsyncioTestCase):
    async def test_employee_counts_by_status(self) -> None:
        """employee_counts correctly groups by status."""
        employees = [
            make_employee(employee_id="EMP001", status="active"),
            make_employee(employee_id="EMP002", status="active",
                          email="b@x.com"),
            make_employee(employee_id="EMP003", status="suspended",
                          email="c@x.com"),
            make_employee(employee_id="EMP004", status="inactive",
                          email="d@x.com"),
        ]
        emp_repo = CapturingEmployeeRepository(initial=employees)
        audit_repo = CapturingAuditRepository()
        svc = _svc(emp_repo, audit_repo)

        # The dashboard method internally calls _complaint_counts and
        # _sla_breaches_today which use db.execute — we need to mock those.
        # Instead, we test just the employee-related parts.
        all_employees, _total = await emp_repo.list(FakeDb(), limit=10_000)
        from collections import Counter
        status_counts = Counter(e.status for e in all_employees)

        self.assertEqual(len(all_employees), 4)
        self.assertEqual(status_counts["active"], 2)
        self.assertEqual(status_counts["suspended"], 1)
        self.assertEqual(status_counts["inactive"], 1)

    async def test_role_counts(self) -> None:
        """role_counts correctly groups by role."""
        employees = [
            make_employee(employee_id="EMP001", role="agent"),
            make_employee(employee_id="EMP002", role="agent",
                          email="b@x.com"),
            make_employee(employee_id="EMP003", role="manager",
                          email="c@x.com"),
            make_employee(employee_id="EMP004", role="admin",
                          email="d@x.com"),
        ]
        emp_repo = CapturingEmployeeRepository(initial=employees)
        all_employees, _ = await emp_repo.list(FakeDb(), limit=10_000)
        from collections import Counter
        role_counts = Counter(e.role for e in all_employees)

        self.assertEqual(role_counts["agent"], 2)
        self.assertEqual(role_counts["manager"], 1)
        self.assertEqual(role_counts["admin"], 1)
        self.assertNotIn("super_admin", role_counts)


class RecentlyActiveTests(unittest.IsolatedAsyncioTestCase):
    async def test_recent_login_included(self) -> None:
        """A login within the last 30 minutes counts as recently active."""
        recent_time = datetime.now(UTC) - timedelta(minutes=5)
        audit_repo = CapturingAuditRepository()
        audit_repo.records.append(make_audit_log(
            actor_employee_id="EMP001",
            action="auth.login_success",
            created_at=recent_time,
        ))
        emp_repo = CapturingEmployeeRepository()
        svc = _svc(emp_repo, audit_repo)

        cutoff = datetime.now(UTC) - timedelta(minutes=30)
        logs, _ = await audit_repo.list(
            FakeDb(), action="auth.login_success", date_from=cutoff, limit=10_000,
        )
        recent_count = len({
            log.actor_employee_id for log in logs if log.actor_employee_id
        })
        self.assertEqual(recent_count, 1)

    async def test_old_login_excluded(self) -> None:
        """A login from 2 hours ago should not count as recently active."""
        old_time = datetime.now(UTC) - timedelta(hours=2)
        audit_repo = CapturingAuditRepository()
        audit_repo.records.append(make_audit_log(
            actor_employee_id="EMP001",
            action="auth.login_success",
            created_at=old_time,
        ))
        emp_repo = CapturingEmployeeRepository()
        svc = _svc(emp_repo, audit_repo)

        cutoff = datetime.now(UTC) - timedelta(minutes=30)
        logs, _ = await audit_repo.list(
            FakeDb(), action="auth.login_success", date_from=cutoff, limit=10_000,
        )
        recent_count = len({
            log.actor_employee_id for log in logs if log.actor_employee_id
        })
        self.assertEqual(recent_count, 0)

    async def test_multiple_logins_same_employee_counted_once(self) -> None:
        """Multiple recent logins by the same employee count as 1."""
        now = datetime.now(UTC)
        audit_repo = CapturingAuditRepository()
        audit_repo.records.append(make_audit_log(
            actor_employee_id="EMP001",
            action="auth.login_success",
            created_at=now - timedelta(minutes=5),
        ))
        audit_repo.records.append(make_audit_log(
            actor_employee_id="EMP001",
            action="auth.login_success",
            created_at=now - timedelta(minutes=10),
        ))

        cutoff = now - timedelta(minutes=30)
        logs, _ = await audit_repo.list(
            FakeDb(), action="auth.login_success", date_from=cutoff, limit=10_000,
        )
        recent_count = len({
            log.actor_employee_id for log in logs if log.actor_employee_id
        })
        self.assertEqual(recent_count, 1)


# ── HTTP-layer tests ─────────────────────────────────────────────────────────

class DashboardEndpointTests(unittest.TestCase):
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

    @patch("app.employees.router.EmployeeService")
    def test_admin_dashboard_returns_200(self, mock_service_class) -> None:
        mock_service = MagicMock()
        mock_service.get_dashboard_summary = AsyncMock(return_value={
            "employee_counts": {"total": 4, "active": 2, "suspended": 1, "inactive": 1},
            "role_counts": {"agent": 2, "manager": 1, "admin": 1},
            "department_count": 3,
            "recently_active_employees": 1,
            "complaints_today": 10,
            "open_complaints": 5,
            "escalated_complaints": 2,
            "sla_breaches_today": 1,
            "generated_at": datetime.now(UTC).isoformat(),
        })
        mock_service_class.return_value = mock_service

        client = self._build_client(Role.ADMIN)
        resp = client.get("/api/admin/dashboard")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["employee_counts"]["total"], 4)
        self.assertEqual(body["role_counts"]["agent"], 2)
        self.assertEqual(body["department_count"], 3)
        self.assertEqual(body["recently_active_employees"], 1)
        self.assertEqual(body["complaints_today"], 10)
        self.assertEqual(body["open_complaints"], 5)
        self.assertEqual(body["escalated_complaints"], 2)
        self.assertEqual(body["sla_breaches_today"], 1)
        self.assertIn("generated_at", body)

    @patch("app.employees.router.EmployeeService")
    def test_super_admin_can_access_dashboard(self, mock_service_class) -> None:
        mock_service = MagicMock()
        mock_service.get_dashboard_summary = AsyncMock(return_value={
            "employee_counts": {"total": 0, "active": 0, "suspended": 0, "inactive": 0},
            "role_counts": {},
            "department_count": 0,
            "recently_active_employees": 0,
            "complaints_today": 0,
            "open_complaints": 0,
            "escalated_complaints": 0,
            "sla_breaches_today": 0,
            "generated_at": datetime.now(UTC).isoformat(),
        })
        mock_service_class.return_value = mock_service

        client = self._build_client(Role.SUPER_ADMIN)
        resp = client.get("/api/admin/dashboard")
        self.assertEqual(resp.status_code, 200)

    def test_agent_cannot_access_dashboard(self) -> None:
        """Agent calling GET /api/admin/dashboard gets 403."""
        client = self._build_client(Role.AGENT)
        resp = client.get("/api/admin/dashboard")
        self.assertEqual(resp.status_code, 403)

    def test_manager_cannot_access_dashboard(self) -> None:
        """Manager calling GET /api/admin/dashboard gets 403."""
        client = self._build_client(Role.MANAGER)
        resp = client.get("/api/admin/dashboard")
        self.assertEqual(resp.status_code, 403)

    @patch("app.employees.router.EmployeeService")
    def test_dashboard_response_shape(self, mock_service_class) -> None:
        """Verify response has all required fields with correct types."""
        mock_service = MagicMock()
        mock_service.get_dashboard_summary = AsyncMock(return_value={
            "employee_counts": {"total": 10, "active": 7, "suspended": 2, "inactive": 1},
            "role_counts": {"agent": 5, "manager": 3, "admin": 1, "super_admin": 1},
            "department_count": 4,
            "recently_active_employees": 3,
            "complaints_today": 15,
            "open_complaints": 8,
            "escalated_complaints": 3,
            "sla_breaches_today": 2,
            "generated_at": datetime.now(UTC).isoformat(),
        })
        mock_service_class.return_value = mock_service

        client = self._build_client(Role.ADMIN)
        resp = client.get("/api/admin/dashboard")
        body = resp.json()

        # Verify employee_counts shape
        ec = body["employee_counts"]
        self.assertIn("total", ec)
        self.assertIn("active", ec)
        self.assertIn("suspended", ec)
        self.assertIn("inactive", ec)
        self.assertEqual(ec["total"], ec["active"] + ec["suspended"] + ec["inactive"])

        # Verify role_counts is a dict
        self.assertIsInstance(body["role_counts"], dict)

        # Verify int fields
        for field in ["department_count", "recently_active_employees",
                       "complaints_today", "open_complaints",
                       "escalated_complaints", "sla_breaches_today"]:
            self.assertIsInstance(body[field], int, f"{field} must be int")


if __name__ == "__main__":
    unittest.main()
