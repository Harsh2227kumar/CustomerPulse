"""Tests for role permissions map and role-change guard rails.

Covers:
    - GET /api/admin/roles returns correct map and per-caller scoped capabilities
    - Admin cannot promote another employee to admin or super_admin (403)
    - Super_admin CAN promote an employee to admin (success)
    - Any employee (including super_admin) cannot change their own role (403)
    - Non-role PATCH fields by admin still work (regression guard)
"""
import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost/test")
os.environ.setdefault("BEDROCK_API_KEY", "test-key")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.constants import Role
from app.core.security import Principal, get_current_principal
from app.db.session import get_db_session
from app.employees.permissions import ROLE_CAPABILITIES, all_roles_map, capabilities_for
from app.employees.router import admin_router
from app.employees.schemas import EmployeeUpdate
from app.employees.service import (
    EmployeeService,
    RoleChangeNotPermittedError,
)

from tests.employees.conftest import (
    CapturingAuditRepository,
    CapturingEmployeeRepository,
    FakeDb,
    make_employee,
)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _build_client(role: Role, actor: str = "EMP999") -> TestClient:
    app = FastAPI()
    app.include_router(admin_router)

    async def _override_db():
        yield object()

    app.dependency_overrides[get_db_session] = _override_db
    app.dependency_overrides[get_current_principal] = lambda: Principal(
        actor=actor, role=role
    )
    return TestClient(app)


def _svc(emp_repo=None, audit_repo=None) -> EmployeeService:
    return EmployeeService(
        employee_repo=emp_repo or CapturingEmployeeRepository(),
        audit_repo=audit_repo or CapturingAuditRepository(),
    )


# ─── TASK 1 unit tests — capability map structure ─────────────────────────────

class CapabilityMapTests(unittest.TestCase):
    def test_all_roles_are_present(self) -> None:
        self.assertEqual(set(ROLE_CAPABILITIES.keys()), set(Role))

    def test_capabilities_for_returns_list(self) -> None:
        caps = capabilities_for(Role.AGENT)
        self.assertIsInstance(caps, list)
        self.assertTrue(len(caps) > 0)

    def test_capabilities_for_accepts_string_role(self) -> None:
        caps_str = capabilities_for("manager")
        caps_enum = capabilities_for(Role.MANAGER)
        self.assertEqual(caps_str, caps_enum)

    def test_super_admin_has_more_caps_than_admin(self) -> None:
        admin_caps = set(capabilities_for(Role.ADMIN))
        super_caps = set(capabilities_for(Role.SUPER_ADMIN))
        self.assertTrue(admin_caps.issubset(super_caps))
        self.assertIn("manage_admins", super_caps)
        self.assertNotIn("manage_admins", admin_caps)

    def test_all_roles_map_is_json_serialisable(self) -> None:
        import json
        data = all_roles_map()
        dumped = json.dumps(data)  # must not raise
        loaded = json.loads(dumped)
        self.assertIn("agent", loaded)
        self.assertIn("super_admin", loaded)

    def test_audit_logs_are_never_deletable(self) -> None:
        """Regression: 'delete_audit_logs' must not appear in any role."""
        all_caps = {cap for caps in ROLE_CAPABILITIES.values() for cap in caps}
        self.assertNotIn("delete_audit_logs", all_caps)


# ─── TASK 2 — GET /api/admin/roles endpoint ───────────────────────────────────

class RolesEndpointTests(unittest.TestCase):
    def _get_roles(self, role: Role, actor: str = "EMP999") -> dict:
        client = _build_client(role, actor=actor)
        resp = client.get("/api/admin/roles")
        self.assertEqual(resp.status_code, 200, resp.text)
        return resp.json()

    def test_returns_all_roles_map(self) -> None:
        body = self._get_roles(Role.AGENT)
        self.assertIn("all_roles", body)
        self.assertEqual(set(body["all_roles"].keys()), {"agent", "manager", "admin", "super_admin"})

    def test_your_role_matches_caller(self) -> None:
        body = self._get_roles(Role.MANAGER)
        self.assertEqual(body["your_role"], "manager")

    def test_your_capabilities_matches_role(self) -> None:
        body = self._get_roles(Role.ADMIN)
        expected = capabilities_for(Role.ADMIN)
        self.assertEqual(body["your_capabilities"], expected)

    def test_agent_capabilities_are_correctly_scoped(self) -> None:
        body = self._get_roles(Role.AGENT)
        self.assertIn("view_assigned_complaints", body["your_capabilities"])
        self.assertNotIn("manage_employees", body["your_capabilities"])
        self.assertNotIn("manage_admins", body["your_capabilities"])

    def test_super_admin_capabilities_include_manage_admins(self) -> None:
        body = self._get_roles(Role.SUPER_ADMIN)
        self.assertIn("manage_admins", body["your_capabilities"])

    def test_endpoint_accessible_to_any_authenticated_role(self) -> None:
        for role in Role:
            body = self._get_roles(role)
            self.assertIn("your_role", body)


# ─── TASK 3 — Role-change guard rails (service layer) ────────────────────────

class RoleChangeGuardTests(unittest.IsolatedAsyncioTestCase):
    async def test_admin_cannot_promote_to_admin(self) -> None:
        target = make_employee(role="agent", employee_id="EMP001")
        emp_repo = CapturingEmployeeRepository(initial=[target])
        svc = _svc(emp_repo)

        with self.assertRaises(RoleChangeNotPermittedError) as ctx:
            await svc.update_employee(
                FakeDb(),
                "EMP001",
                EmployeeUpdate(role="admin"),
                actor_employee_id="EMP999",
                actor_role="admin",
            )
        self.assertIn("super_admin", str(ctx.exception))

    async def test_admin_cannot_promote_to_super_admin(self) -> None:
        target = make_employee(role="agent", employee_id="EMP001")
        emp_repo = CapturingEmployeeRepository(initial=[target])
        svc = _svc(emp_repo)

        with self.assertRaises(RoleChangeNotPermittedError):
            await svc.update_employee(
                FakeDb(),
                "EMP001",
                EmployeeUpdate(role="super_admin"),
                actor_employee_id="EMP999",
                actor_role="admin",
            )

    async def test_super_admin_can_promote_to_admin(self) -> None:
        target = make_employee(role="agent", employee_id="EMP001")
        emp_repo = CapturingEmployeeRepository(initial=[target])
        svc = _svc(emp_repo)

        result = await svc.update_employee(
            FakeDb(),
            "EMP001",
            EmployeeUpdate(role="admin"),
            actor_employee_id="EMP999",
            actor_role="super_admin",
        )
        self.assertEqual(result.role, "admin")

    async def test_super_admin_can_promote_to_super_admin(self) -> None:
        target = make_employee(role="agent", employee_id="EMP001")
        emp_repo = CapturingEmployeeRepository(initial=[target])
        svc = _svc(emp_repo)

        result = await svc.update_employee(
            FakeDb(),
            "EMP001",
            EmployeeUpdate(role="super_admin"),
            actor_employee_id="EMP999",
            actor_role="super_admin",
        )
        self.assertEqual(result.role, "super_admin")

    async def test_self_promotion_blocked_for_admin(self) -> None:
        actor = make_employee(role="admin", employee_id="EMP999")
        emp_repo = CapturingEmployeeRepository(initial=[actor])
        svc = _svc(emp_repo)

        with self.assertRaises(RoleChangeNotPermittedError) as ctx:
            await svc.update_employee(
                FakeDb(),
                "EMP999",
                EmployeeUpdate(role="super_admin"),
                actor_employee_id="EMP999",
                actor_role="admin",
            )
        self.assertIn("own role", str(ctx.exception))

    async def test_self_promotion_blocked_for_super_admin(self) -> None:
        """Even super_admin cannot change their own role."""
        actor = make_employee(role="super_admin", employee_id="EMP001")
        emp_repo = CapturingEmployeeRepository(initial=[actor])
        svc = _svc(emp_repo)

        with self.assertRaises(RoleChangeNotPermittedError):
            await svc.update_employee(
                FakeDb(),
                "EMP001",
                EmployeeUpdate(role="admin"),
                actor_employee_id="EMP001",
                actor_role="super_admin",
            )

    async def test_manager_cannot_promote_anyone_to_admin(self) -> None:
        target = make_employee(role="agent", employee_id="EMP001")
        emp_repo = CapturingEmployeeRepository(initial=[target])
        svc = _svc(emp_repo)

        with self.assertRaises(RoleChangeNotPermittedError):
            await svc.update_employee(
                FakeDb(),
                "EMP001",
                EmployeeUpdate(role="admin"),
                actor_employee_id="EMP999",
                actor_role="manager",
            )

    async def test_non_role_fields_by_admin_still_work(self) -> None:
        """Regression: role guard must not block unrelated PATCH fields."""
        target = make_employee(name="Old Name", role="agent", employee_id="EMP001")
        emp_repo = CapturingEmployeeRepository(initial=[target])
        svc = _svc(emp_repo)

        result = await svc.update_employee(
            FakeDb(),
            "EMP001",
            EmployeeUpdate(name="New Name"),  # no role change
            actor_employee_id="EMP999",
            actor_role="admin",
        )
        self.assertEqual(result.name, "New Name")

    async def test_role_change_to_same_role_is_allowed(self) -> None:
        """Setting role=current_role is a no-op — must not raise."""
        target = make_employee(role="manager", employee_id="EMP001")
        emp_repo = CapturingEmployeeRepository(initial=[target])
        svc = _svc(emp_repo)

        # no-op (role unchanged): should succeed without raising
        result = await svc.update_employee(
            FakeDb(),
            "EMP001",
            EmployeeUpdate(role="manager"),
            actor_employee_id="EMP999",
            actor_role="admin",
        )
        self.assertEqual(result.role, "manager")


# ─── TASK 3 — HTTP-layer 403 mapping ─────────────────────────────────────────

class RoleChangeHTTPTests(unittest.TestCase):
    @patch("app.employees.router.EmployeeService")
    def test_patch_admin_role_by_admin_returns_403(self, mock_service_class) -> None:
        mock_service = MagicMock()
        mock_service.update_employee = AsyncMock(
            side_effect=RoleChangeNotPermittedError("Only super_admin can assign admin-level roles.")
        )
        mock_service_class.return_value = mock_service

        client = _build_client(Role.ADMIN, actor="EMP999")
        response = client.patch(
            "/api/admin/employees/EMP001",
            json={"role": "admin"},
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("super_admin", response.json()["detail"])

    @patch("app.employees.router.EmployeeService")
    def test_self_promotion_returns_403(self, mock_service_class) -> None:
        mock_service = MagicMock()
        mock_service.update_employee = AsyncMock(
            side_effect=RoleChangeNotPermittedError("Cannot change your own role.")
        )
        mock_service_class.return_value = mock_service

        client = _build_client(Role.SUPER_ADMIN, actor="EMP001")
        response = client.patch(
            "/api/admin/employees/EMP001",
            json={"role": "admin"},
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("own role", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()
