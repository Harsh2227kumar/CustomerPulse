"""Tests for reporting-chain validation, demotion guard, and reassignment.

Phase 3 coverage:
    - Cannot set reports_to to self.
    - Cannot set reports_to to an agent (must be manager+).
    - Direct cycle blocked (A reports to B, try setting B reports to A).
    - Transitive cycle blocked (A→B→C, try setting C reports to A).
    - Valid reassignment succeeds and produces correct audit details.
    - Admin cannot change a super_admin's role (demotion guard).
    - Admin cannot change another admin's role even sideways to manager.
    - Super_admin CAN change an admin's role.
    - Regression: existing Phase 2 role-guard tests still pass unmodified.
"""
import os
import sys
import unittest

os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost/test")
os.environ.setdefault("BEDROCK_API_KEY", "test-key")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.employees.schemas import EmployeeUpdate
from app.employees.service import (
    EmployeeService,
    InvalidReportsToError,
    RoleChangeNotPermittedError,
)

from tests.employees.conftest import (
    CapturingAuditRepository,
    CapturingEmployeeRepository,
    FakeDb,
    make_employee,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _svc(emp_repo=None, audit_repo=None) -> EmployeeService:
    return EmployeeService(
        employee_repo=emp_repo or CapturingEmployeeRepository(),
        audit_repo=audit_repo or CapturingAuditRepository(),
    )


# ── TASK 2 — Reporting-chain validation ───────────────────────────────────────

class ReportsToValidationTests(unittest.IsolatedAsyncioTestCase):
    async def test_cannot_set_reports_to_self(self) -> None:
        """Setting reports_to to the employee's own id must raise."""
        emp = make_employee(role="agent", employee_id="EMP001")
        emp_repo = CapturingEmployeeRepository(initial=[emp])
        svc = _svc(emp_repo)

        with self.assertRaises(InvalidReportsToError) as ctx:
            await svc.validate_reports_to(FakeDb(), emp.id, emp.id)
        self.assertIn("self", str(ctx.exception))

    async def test_cannot_set_reports_to_agent(self) -> None:
        """Target must be manager or higher — agents cannot be a reports_to target."""
        emp = make_employee(role="agent", employee_id="EMP001")
        agent_target = make_employee(role="agent", employee_id="EMP002")
        emp_repo = CapturingEmployeeRepository(initial=[emp, agent_target])
        svc = _svc(emp_repo)

        with self.assertRaises(InvalidReportsToError) as ctx:
            await svc.validate_reports_to(FakeDb(), emp.id, agent_target.id)
        self.assertIn("manager or higher", str(ctx.exception))

    async def test_direct_cycle_blocked(self) -> None:
        """A reports to B; setting B reports to A must be blocked."""
        mgr_b = make_employee(role="manager", employee_id="EMP_B", reports_to=None)
        mgr_a = make_employee(role="manager", employee_id="EMP_A", reports_to=mgr_b.id)
        emp_repo = CapturingEmployeeRepository(initial=[mgr_a, mgr_b])
        svc = _svc(emp_repo)

        # A.reports_to = B.id.  Setting B.reports_to = A.id would create A→B→A.
        # Walk from A: A.reports_to = B.id → B.id == employee_id (mgr_b.id) → cycle
        with self.assertRaises(InvalidReportsToError) as ctx:
            await svc.validate_reports_to(FakeDb(), mgr_b.id, mgr_a.id)
        self.assertIn("circular", str(ctx.exception))

    async def test_transitive_cycle_blocked(self) -> None:
        """A→B→C chain; setting C reports to A must be blocked."""
        mgr_c = make_employee(role="manager", employee_id="EMP_C", reports_to=None)
        mgr_b = make_employee(role="manager", employee_id="EMP_B", reports_to=mgr_c.id)
        mgr_a = make_employee(role="manager", employee_id="EMP_A", reports_to=mgr_b.id)
        emp_repo = CapturingEmployeeRepository(initial=[mgr_a, mgr_b, mgr_c])
        svc = _svc(emp_repo)

        # Trying to set C.reports_to = A.id
        # Walk from A: A.reports_to = B.id → B.reports_to = C.id → C.id == employee_id → cycle
        with self.assertRaises(InvalidReportsToError) as ctx:
            await svc.validate_reports_to(FakeDb(), mgr_c.id, mgr_a.id)
        self.assertIn("circular", str(ctx.exception))

    async def test_valid_reassignment_succeeds_with_audit(self) -> None:
        """Valid reassignment updates fields and writes correct audit details."""
        mgr = make_employee(role="manager", employee_id="EMP_MGR")
        agent = make_employee(
            role="agent", employee_id="EMP001",
            department_id="old-dept", reports_to=None,
        )
        audit_repo = CapturingAuditRepository()
        emp_repo = CapturingEmployeeRepository(initial=[agent, mgr])
        svc = _svc(emp_repo, audit_repo)

        result = await svc.reassign_employee(
            FakeDb(),
            "EMP001",
            department_id="new-dept",
            reports_to=mgr.id,
            actor_employee_id="EMP999",
        )

        self.assertEqual(result.department_id, "new-dept")
        self.assertEqual(result.reports_to, mgr.id)

        # Verify audit log
        self.assertEqual(len(audit_repo.records), 1)
        log = audit_repo.records[0]
        self.assertEqual(log.action, "employee.reassigned")
        self.assertEqual(log.details["old_department_id"], "old-dept")
        self.assertEqual(log.details["new_department_id"], "new-dept")
        self.assertIsNone(log.details["old_reports_to"])
        self.assertEqual(log.details["new_reports_to"], mgr.id)


# ── TASK 1 — Demotion guard ──────────────────────────────────────────────────

class DemotionGuardTests(unittest.IsolatedAsyncioTestCase):
    async def test_admin_cannot_change_super_admin_role(self) -> None:
        """Admin attempting to change a super_admin's role must be blocked."""
        target = make_employee(role="super_admin", employee_id="EMP_SA")
        emp_repo = CapturingEmployeeRepository(initial=[target])
        svc = _svc(emp_repo)

        with self.assertRaises(RoleChangeNotPermittedError) as ctx:
            await svc.update_employee(
                FakeDb(),
                "EMP_SA",
                EmployeeUpdate(role="manager"),
                actor_employee_id="EMP_ADMIN",
                actor_role="admin",
            )
        self.assertIn("admin-level employee", str(ctx.exception))

    async def test_admin_cannot_change_another_admin_role_sideways(self) -> None:
        """Admin cannot change another admin's role even sideways to manager."""
        target = make_employee(role="admin", employee_id="EMP_A2")
        emp_repo = CapturingEmployeeRepository(initial=[target])
        svc = _svc(emp_repo)

        with self.assertRaises(RoleChangeNotPermittedError) as ctx:
            await svc.update_employee(
                FakeDb(),
                "EMP_A2",
                EmployeeUpdate(role="manager"),
                actor_employee_id="EMP_A1",
                actor_role="admin",
            )
        self.assertIn("admin-level employee", str(ctx.exception))

    async def test_super_admin_can_change_admin_role(self) -> None:
        """Super_admin CAN change an admin's role (e.g. demote to manager)."""
        target = make_employee(role="admin", employee_id="EMP_A1")
        emp_repo = CapturingEmployeeRepository(initial=[target])
        svc = _svc(emp_repo)

        result = await svc.update_employee(
            FakeDb(),
            "EMP_A1",
            EmployeeUpdate(role="manager"),
            actor_employee_id="EMP_SA",
            actor_role="super_admin",
        )
        self.assertEqual(result.role, "manager")


# ── Regression — Phase 2 guards still work ────────────────────────────────────

class Phase2RegressionTests(unittest.IsolatedAsyncioTestCase):
    """Re-run key Phase 2 scenarios to ensure the new guards don't break them."""

    async def test_admin_cannot_promote_to_admin(self) -> None:
        target = make_employee(role="agent", employee_id="EMP001")
        emp_repo = CapturingEmployeeRepository(initial=[target])
        svc = _svc(emp_repo)

        with self.assertRaises(RoleChangeNotPermittedError):
            await svc.update_employee(
                FakeDb(), "EMP001", EmployeeUpdate(role="admin"),
                actor_employee_id="EMP999", actor_role="admin",
            )

    async def test_self_promotion_blocked(self) -> None:
        actor = make_employee(role="admin", employee_id="EMP999")
        emp_repo = CapturingEmployeeRepository(initial=[actor])
        svc = _svc(emp_repo)

        with self.assertRaises(RoleChangeNotPermittedError):
            await svc.update_employee(
                FakeDb(), "EMP999", EmployeeUpdate(role="super_admin"),
                actor_employee_id="EMP999", actor_role="admin",
            )

    async def test_super_admin_can_promote_to_admin(self) -> None:
        target = make_employee(role="agent", employee_id="EMP001")
        emp_repo = CapturingEmployeeRepository(initial=[target])
        svc = _svc(emp_repo)

        result = await svc.update_employee(
            FakeDb(), "EMP001", EmployeeUpdate(role="admin"),
            actor_employee_id="EMP999", actor_role="super_admin",
        )
        self.assertEqual(result.role, "admin")


if __name__ == "__main__":
    unittest.main()
