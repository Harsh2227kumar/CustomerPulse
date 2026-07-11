"""Audit trail tests.

Asserts that each modifying action produces exactly one AuditLog row with the
correct ``action`` string and required ``details`` keys.
"""
import os
import sys
import unittest

os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost/test")
os.environ.setdefault("BEDROCK_API_KEY", "test-key")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from tests.employees.conftest import (
    CapturingAuditRepository,
    CapturingEmployeeRepository,
    FakeDb,
    make_employee,
)
from app.employees.schemas import EmployeeUpdate
from app.employees.service import EmployeeService, hash_password


def _service(emp_repo=None, audit_repo=None) -> EmployeeService:
    return EmployeeService(
        employee_repo=emp_repo or CapturingEmployeeRepository(),
        audit_repo=audit_repo or CapturingAuditRepository(),
    )


class SuspendAuditTests(unittest.IsolatedAsyncioTestCase):
    async def test_suspend_produces_exactly_one_audit_row(self) -> None:
        emp = make_employee(status="active")
        emp_repo = CapturingEmployeeRepository(initial=[emp])
        audit_repo = CapturingAuditRepository()
        svc = _service(emp_repo, audit_repo)

        await svc.suspend_employee(
            FakeDb(), emp.employee_id, actor_employee_id="EMP999", reason="Test reason"
        )

        self.assertEqual(len(audit_repo.records), 1)
        log = audit_repo.records[0]
        self.assertEqual(log.action, "employee.suspended")
        self.assertIn("reason", log.details)
        self.assertEqual(log.details["reason"], "Test reason")

    async def test_lock_produces_employee_locked_action(self) -> None:
        emp = make_employee(status="active")
        emp_repo = CapturingEmployeeRepository(initial=[emp])
        audit_repo = CapturingAuditRepository()
        svc = _service(emp_repo, audit_repo)

        await svc.lock_employee(FakeDb(), emp.employee_id, actor_employee_id="EMP999")

        self.assertEqual(len(audit_repo.records), 1)
        log = audit_repo.records[0]
        self.assertEqual(log.action, "employee.locked")
        self.assertEqual(log.details.get("reason"), "account_locked")


class ActivateAuditTests(unittest.IsolatedAsyncioTestCase):
    async def test_activate_produces_exactly_one_audit_row(self) -> None:
        emp = make_employee(status="suspended")
        emp_repo = CapturingEmployeeRepository(initial=[emp])
        audit_repo = CapturingAuditRepository()
        svc = _service(emp_repo, audit_repo)

        await svc.activate_employee(FakeDb(), emp.employee_id, actor_employee_id="EMP999")

        self.assertEqual(len(audit_repo.records), 1)
        self.assertEqual(audit_repo.records[0].action, "employee.activated")

    async def test_unlock_produces_employee_unlocked_action(self) -> None:
        emp = make_employee(status="suspended")
        emp_repo = CapturingEmployeeRepository(initial=[emp])
        audit_repo = CapturingAuditRepository()
        svc = _service(emp_repo, audit_repo)

        await svc.unlock_employee(FakeDb(), emp.employee_id, actor_employee_id="EMP999")

        self.assertEqual(len(audit_repo.records), 1)
        self.assertEqual(audit_repo.records[0].action, "employee.unlocked")


class ResetPasswordAuditTests(unittest.IsolatedAsyncioTestCase):
    async def test_reset_password_produces_exactly_one_audit_row(self) -> None:
        emp = make_employee()
        emp_repo = CapturingEmployeeRepository(initial=[emp])
        audit_repo = CapturingAuditRepository()
        svc = _service(emp_repo, audit_repo)

        _emp, temp_pwd = await svc.reset_password(
            FakeDb(), emp.employee_id, actor_employee_id="EMP999"
        )

        self.assertEqual(len(audit_repo.records), 1)
        log = audit_repo.records[0]
        self.assertEqual(log.action, "employee.password_reset")

    async def test_reset_password_does_not_log_plaintext(self) -> None:
        emp = make_employee()
        emp_repo = CapturingEmployeeRepository(initial=[emp])
        audit_repo = CapturingAuditRepository()
        svc = _service(emp_repo, audit_repo)

        _emp, temp_pwd = await svc.reset_password(
            FakeDb(), emp.employee_id, actor_employee_id="EMP999"
        )
        log = audit_repo.records[0]
        # The plaintext temp password must never appear in audit details
        details_str = str(log.details or "")
        self.assertNotIn(temp_pwd, details_str)


class UpdateAuditTests(unittest.IsolatedAsyncioTestCase):
    async def test_update_produces_exactly_one_audit_row(self) -> None:
        emp = make_employee(name="Original", role="agent")
        emp_repo = CapturingEmployeeRepository(initial=[emp])
        audit_repo = CapturingAuditRepository()
        svc = _service(emp_repo, audit_repo)

        await svc.update_employee(
            FakeDb(),
            emp.employee_id,
            EmployeeUpdate(name="Updated"),
            actor_employee_id="EMP999",
        )

        self.assertEqual(len(audit_repo.records), 1)
        log = audit_repo.records[0]
        self.assertEqual(log.action, "employee.updated")

    async def test_update_audit_contains_old_and_new_values(self) -> None:
        emp = make_employee(name="Alice", role="agent")
        emp_repo = CapturingEmployeeRepository(initial=[emp])
        audit_repo = CapturingAuditRepository()
        svc = _service(emp_repo, audit_repo)

        await svc.update_employee(
            FakeDb(),
            emp.employee_id,
            EmployeeUpdate(name="Bob", role="manager"),
            actor_employee_id="EMP999",
        )

        log = audit_repo.records[0]
        changes = log.details["changes"]

        self.assertIn("name", changes)
        self.assertEqual(changes["name"]["old_value"], "Alice")
        self.assertEqual(changes["name"]["new_value"], "Bob")

        self.assertIn("role", changes)
        self.assertEqual(changes["role"]["old_value"], "agent")
        self.assertEqual(changes["role"]["new_value"], "manager")

    async def test_update_noop_produces_no_audit_row(self) -> None:
        emp = make_employee(name="Same")
        emp_repo = CapturingEmployeeRepository(initial=[emp])
        audit_repo = CapturingAuditRepository()
        svc = _service(emp_repo, audit_repo)

        await svc.update_employee(
            FakeDb(),
            emp.employee_id,
            EmployeeUpdate(name="Same"),
            actor_employee_id="EMP999",
        )
        # Nothing changed → no audit entry
        self.assertEqual(len(audit_repo.records), 0)


if __name__ == "__main__":
    unittest.main()
