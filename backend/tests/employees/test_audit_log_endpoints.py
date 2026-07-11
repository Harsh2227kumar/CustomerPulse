"""Tests for audit-log endpoints, login history, and /me/audit-logs.

Covers:
    - GET /api/admin/audit-logs returns entries, filterable by action and target_type.
    - GET /api/admin/login-history with success=true/false filters correctly.
    - GET /api/admin/login-history excludes non-login actions.
    - Manager/agent calling GET /api/admin/audit-logs gets 403.
    - GET /api/me/audit-logs returns only the caller's own rows even if a
      different actor_employee_id is passed as a query param.
    - actor_name resolves correctly for known employees and is null for
      system-initiated entries.
"""
import os
import sys
import unittest
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
    FakeDb,
    make_employee,
    make_audit_log,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _svc(emp_repo=None, audit_repo=None) -> EmployeeService:
    return EmployeeService(
        employee_repo=emp_repo or CapturingEmployeeRepository(),
        audit_repo=audit_repo or CapturingAuditRepository(),
    )


def _seed_audit_repo() -> CapturingAuditRepository:
    """Create a pre-seeded audit repo with a mix of actions."""
    repo = CapturingAuditRepository()
    # Login entries
    repo.records.append(make_audit_log(
        actor_employee_id="EMP001", action="auth.login_success",
        target_type="employee", details={"email": "jane@example.com"},
    ))
    repo.records.append(make_audit_log(
        actor_employee_id="EMP001", action="auth.login_failed",
        target_type="employee", details={"email": "jane@example.com", "reason": "incorrect_password"},
    ))
    repo.records.append(make_audit_log(
        actor_employee_id="EMP002", action="auth.login_success",
        target_type="employee", details={"email": "bob@example.com"},
    ))
    # Non-login entries
    repo.records.append(make_audit_log(
        actor_employee_id="EMP001", action="employee.suspended",
        target_type="employee", details={"reason": "policy violation"},
    ))
    repo.records.append(make_audit_log(
        actor_employee_id="EMP001", action="employee.updated",
        target_type="employee", details={"changes": {"name": {"old_value": "Old", "new_value": "New"}}},
    ))
    # System-initiated entry (no actor)
    repo.records.append(make_audit_log(
        actor_employee_id=None, action="auth.login_failed",
        target_type="employee", details={"email": "unknown@example.com", "reason": "user_not_found"},
    ))
    return repo


# ── TASK 4 — Service-layer tests ─────────────────────────────────────────────

class AuditLogServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_list_audit_logs_returns_all_entries(self) -> None:
        """list_audit_logs without filters returns all entries."""
        audit_repo = _seed_audit_repo()
        emp_repo = CapturingEmployeeRepository(initial=[
            make_employee(employee_id="EMP001", name="Jane Doe"),
        ])
        svc = _svc(emp_repo, audit_repo)

        items, total = await svc.list_audit_logs(FakeDb())
        self.assertEqual(total, 6)
        self.assertEqual(len(items), 6)

    async def test_filter_by_action(self) -> None:
        """Exact action filter works."""
        audit_repo = _seed_audit_repo()
        emp_repo = CapturingEmployeeRepository()
        svc = _svc(emp_repo, audit_repo)

        items, total = await svc.list_audit_logs(
            FakeDb(), action="employee.suspended",
        )
        self.assertEqual(total, 1)
        self.assertEqual(items[0]["action"], "employee.suspended")

    async def test_filter_by_target_type(self) -> None:
        """target_type filter works."""
        audit_repo = _seed_audit_repo()
        emp_repo = CapturingEmployeeRepository()
        svc = _svc(emp_repo, audit_repo)

        items, total = await svc.list_audit_logs(
            FakeDb(), target_type="employee",
        )
        self.assertEqual(total, 6)  # all entries in seed have target_type="employee"

    async def test_action_prefix_filters_login_entries_only(self) -> None:
        """action_prefix='auth.login' returns only login-related entries."""
        audit_repo = _seed_audit_repo()
        emp_repo = CapturingEmployeeRepository()
        svc = _svc(emp_repo, audit_repo)

        items, total = await svc.list_audit_logs(
            FakeDb(), action_prefix="auth.login",
        )
        self.assertEqual(total, 4)  # 2 success + 2 failed
        for item in items:
            self.assertTrue(item["action"].startswith("auth.login"))

    async def test_login_history_success_only(self) -> None:
        """Filtering by exact action='auth.login_success' returns only successes."""
        audit_repo = _seed_audit_repo()
        emp_repo = CapturingEmployeeRepository()
        svc = _svc(emp_repo, audit_repo)

        items, total = await svc.list_audit_logs(
            FakeDb(), action="auth.login_success",
        )
        self.assertEqual(total, 2)
        for item in items:
            self.assertEqual(item["action"], "auth.login_success")

    async def test_login_history_failed_only(self) -> None:
        """Filtering by exact action='auth.login_failed' returns only failures."""
        audit_repo = _seed_audit_repo()
        emp_repo = CapturingEmployeeRepository()
        svc = _svc(emp_repo, audit_repo)

        items, total = await svc.list_audit_logs(
            FakeDb(), action="auth.login_failed",
        )
        self.assertEqual(total, 2)
        for item in items:
            self.assertEqual(item["action"], "auth.login_failed")

    async def test_login_history_excludes_non_login_actions(self) -> None:
        """action_prefix='auth.login' must not include employee.suspended etc."""
        audit_repo = _seed_audit_repo()
        emp_repo = CapturingEmployeeRepository()
        svc = _svc(emp_repo, audit_repo)

        items, total = await svc.list_audit_logs(
            FakeDb(), action_prefix="auth.login",
        )
        non_login = [i for i in items if not i["action"].startswith("auth.login")]
        self.assertEqual(len(non_login), 0)

    async def test_actor_name_resolved_for_known_employee(self) -> None:
        """actor_name should be the employee's name when actor_employee_id is known."""
        audit_repo = _seed_audit_repo()
        emp_repo = CapturingEmployeeRepository(initial=[
            make_employee(employee_id="EMP001", name="Jane Doe"),
        ])
        svc = _svc(emp_repo, audit_repo)

        items, total = await svc.list_audit_logs(
            FakeDb(), actor_employee_id="EMP001",
        )
        self.assertTrue(len(items) > 0)
        for item in items:
            self.assertEqual(item["actor_name"], "Jane Doe")

    async def test_actor_name_null_for_system_entries(self) -> None:
        """System-initiated entries (no actor) should have actor_name=None."""
        audit_repo = _seed_audit_repo()
        emp_repo = CapturingEmployeeRepository()
        svc = _svc(emp_repo, audit_repo)

        items, total = await svc.list_audit_logs(FakeDb())
        system_entries = [i for i in items if i["actor_employee_id"] is None]
        self.assertTrue(len(system_entries) > 0)
        for entry in system_entries:
            self.assertIsNone(entry["actor_name"])

    async def test_me_audit_logs_forces_own_actor_id(self) -> None:
        """list_audit_logs with actor_employee_id returns only that actor's rows."""
        audit_repo = _seed_audit_repo()
        emp_repo = CapturingEmployeeRepository(initial=[
            make_employee(employee_id="EMP001", name="Jane Doe"),
        ])
        svc = _svc(emp_repo, audit_repo)

        # Call with EMP001 — should only get EMP001's rows
        items, total = await svc.list_audit_logs(
            FakeDb(), actor_employee_id="EMP001",
        )
        for item in items:
            self.assertEqual(item["actor_employee_id"], "EMP001")
        # Seed has 4 entries by EMP001
        self.assertEqual(total, 4)


# ── TASK 4 — HTTP-layer tests ────────────────────────────────────────────────

class AuditLogEndpointTests(unittest.TestCase):
    def _build_client(self, role: Role, actor: str = "EMP999"):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from app.employees.router import admin_router, me_router

        app = FastAPI()
        app.include_router(admin_router)
        app.include_router(me_router)

        async def _override_db():
            yield object()

        app.dependency_overrides[get_db_session] = _override_db
        app.dependency_overrides[get_current_principal] = lambda: Principal(
            actor=actor, role=role
        )
        return TestClient(app)

    @patch("app.employees.router.EmployeeService")
    def test_admin_audit_logs_returns_200(self, mock_service_class) -> None:
        mock_service = MagicMock()
        mock_service.list_audit_logs = AsyncMock(return_value=([], 0))
        mock_service_class.return_value = mock_service

        client = self._build_client(Role.ADMIN)
        resp = client.get("/api/admin/audit-logs")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["items"], [])
        self.assertEqual(body["total"], 0)

    @patch("app.employees.router.EmployeeService")
    def test_admin_login_history_returns_200(self, mock_service_class) -> None:
        mock_service = MagicMock()
        mock_service.list_audit_logs = AsyncMock(return_value=([], 0))
        mock_service_class.return_value = mock_service

        client = self._build_client(Role.ADMIN)
        resp = client.get("/api/admin/login-history")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["items"], [])

    def test_agent_cannot_access_admin_audit_logs(self) -> None:
        """Agent calling GET /api/admin/audit-logs gets 403."""
        client = self._build_client(Role.AGENT)
        resp = client.get("/api/admin/audit-logs")
        self.assertEqual(resp.status_code, 403)

    def test_manager_cannot_access_admin_audit_logs(self) -> None:
        """Manager calling GET /api/admin/audit-logs gets 403."""
        client = self._build_client(Role.MANAGER)
        resp = client.get("/api/admin/audit-logs")
        self.assertEqual(resp.status_code, 403)

    @patch("app.employees.router.EmployeeService")
    def test_me_audit_logs_overrides_actor_param(self, mock_service_class) -> None:
        """GET /api/me/audit-logs forces actor_employee_id to caller's own id,
        even if a different one is passed as query param."""
        mock_service = MagicMock()
        mock_service.list_audit_logs = AsyncMock(return_value=([], 0))
        mock_service_class.return_value = mock_service

        client = self._build_client(Role.AGENT, actor="EMP_CALLER")
        # Pass a different actor_employee_id — should be overridden
        resp = client.get("/api/me/audit-logs?actor_employee_id=EMP_OTHER")
        self.assertEqual(resp.status_code, 200)

        # Verify the service was called with the caller's own id
        call_kwargs = mock_service.list_audit_logs.call_args
        self.assertEqual(call_kwargs.kwargs["actor_employee_id"], "EMP_CALLER")

    @patch("app.employees.router.EmployeeService")
    def test_me_audit_logs_accessible_to_any_role(self, mock_service_class) -> None:
        """GET /api/me/audit-logs is accessible to agents, managers, admins, etc."""
        mock_service = MagicMock()
        mock_service.list_audit_logs = AsyncMock(return_value=([], 0))
        mock_service_class.return_value = mock_service

        for role in Role:
            client = self._build_client(role)
            resp = client.get("/api/me/audit-logs")
            self.assertEqual(resp.status_code, 200, f"Role {role} should have access")

    @patch("app.employees.router.EmployeeService")
    def test_login_history_success_filter(self, mock_service_class) -> None:
        """success=true maps to action='auth.login_success'."""
        mock_service = MagicMock()
        mock_service.list_audit_logs = AsyncMock(return_value=([], 0))
        mock_service_class.return_value = mock_service

        client = self._build_client(Role.ADMIN)
        client.get("/api/admin/login-history?success=true")

        call_kwargs = mock_service.list_audit_logs.call_args.kwargs
        self.assertEqual(call_kwargs["action"], "auth.login_success")
        self.assertIsNone(call_kwargs.get("action_prefix"))

    @patch("app.employees.router.EmployeeService")
    def test_login_history_failure_filter(self, mock_service_class) -> None:
        """success=false maps to action='auth.login_failed'."""
        mock_service = MagicMock()
        mock_service.list_audit_logs = AsyncMock(return_value=([], 0))
        mock_service_class.return_value = mock_service

        client = self._build_client(Role.ADMIN)
        client.get("/api/admin/login-history?success=false")

        call_kwargs = mock_service.list_audit_logs.call_args.kwargs
        self.assertEqual(call_kwargs["action"], "auth.login_failed")

    @patch("app.employees.router.EmployeeService")
    def test_login_history_no_success_filter_uses_prefix(self, mock_service_class) -> None:
        """No success param uses action_prefix='auth.login'."""
        mock_service = MagicMock()
        mock_service.list_audit_logs = AsyncMock(return_value=([], 0))
        mock_service_class.return_value = mock_service

        client = self._build_client(Role.ADMIN)
        client.get("/api/admin/login-history")

        call_kwargs = mock_service.list_audit_logs.call_args.kwargs
        self.assertIsNone(call_kwargs.get("action"))
        self.assertEqual(call_kwargs["action_prefix"], "auth.login")


if __name__ == "__main__":
    unittest.main()
