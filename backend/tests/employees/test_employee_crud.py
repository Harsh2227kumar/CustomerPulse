"""Service-level unit tests for employee CRUD operations.

All tests use in-memory capturing repositories from conftest.py — no database,
no FastAPI, no HTTP requests.
"""
import os
import sys
import unittest

# Ensure DATABASE_URL is set before any app imports trigger Settings
os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost/test")
os.environ.setdefault("BEDROCK_API_KEY", "test-key")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from tests.employees.conftest import (
    CapturingAuditRepository,
    CapturingEmployeeRepository,
    FakeDb,
    make_employee,
)
from app.employees.schemas import EmployeeCreate, EmployeeUpdate
from app.employees.service import (
    EmployeeAlreadyActiveError,
    EmployeeAlreadySuspendedError,
    EmployeeEmailConflictError,
    EmployeeNotFoundError,
    EmployeeNotInactiveError,
    EmployeeService,
    InvalidCredentialsError,
    hash_password,
    verify_password,
)


def _service(emp_repo=None, audit_repo=None) -> EmployeeService:
    return EmployeeService(
        employee_repo=emp_repo or CapturingEmployeeRepository(),
        audit_repo=audit_repo or CapturingAuditRepository(),
    )


class CreateEmployeeTests(unittest.IsolatedAsyncioTestCase):
    async def test_create_employee_success(self) -> None:
        emp_repo = CapturingEmployeeRepository()
        audit_repo = CapturingAuditRepository()
        svc = _service(emp_repo, audit_repo)
        db = FakeDb()

        payload = EmployeeCreate(
            name="Alice Smith",
            email="alice@acme.com",
            password="secret123",
            role="agent",
        )
        emp = await svc.create_employee(db, payload, created_by="EMP999")

        self.assertEqual(emp.name, "Alice Smith")
        self.assertEqual(emp.email, "alice@acme.com")
        self.assertEqual(emp.status, "active")
        self.assertFalse(emp.must_change_password)
        self.assertTrue(db.committed)
        self.assertEqual(len(audit_repo.records), 1)
        self.assertEqual(audit_repo.records[0].action, "employee.created")

    async def test_create_employee_email_conflict_raises_409(self) -> None:
        existing = make_employee(email="alice@acme.com")
        emp_repo = CapturingEmployeeRepository(initial=[existing])
        svc = _service(emp_repo)

        payload = EmployeeCreate(
            name="Alice Duplicate",
            email="alice@acme.com",
            password="secret123",
            role="agent",
        )
        with self.assertRaises(EmployeeEmailConflictError):
            await svc.create_employee(FakeDb(), payload)


class ListEmployeesTests(unittest.IsolatedAsyncioTestCase):
    async def test_list_employees_filters_by_role(self) -> None:
        agents = [make_employee(email=f"a{i}@x.com", role="agent") for i in range(3)]
        manager = make_employee(email="m@x.com", role="manager")
        emp_repo = CapturingEmployeeRepository(initial=agents + [manager])
        svc = _service(emp_repo)

        items, total = await svc.list_employees(FakeDb(), role="agent")
        self.assertEqual(total, 3)
        self.assertTrue(all(e.role == "agent" for e in items))

    async def test_list_employees_search_matches_name(self) -> None:
        emp_repo = CapturingEmployeeRepository(initial=[
            make_employee(name="Charlie Brown", email="cb@x.com"),
            make_employee(name="Alice Smith", email="as@x.com", employee_id="EMP002"),
        ])
        svc = _service(emp_repo)

        items, total = await svc.list_employees(FakeDb(), search="charlie")
        self.assertEqual(total, 1)
        self.assertEqual(items[0].name, "Charlie Brown")

    async def test_list_employees_search_matches_email(self) -> None:
        emp_repo = CapturingEmployeeRepository(initial=[
            make_employee(name="A", email="findme@corp.com"),
            make_employee(name="B", email="other@corp.com", employee_id="EMP002"),
        ])
        svc = _service(emp_repo)

        items, total = await svc.list_employees(FakeDb(), search="findme")
        self.assertEqual(total, 1)
        self.assertEqual(items[0].email, "findme@corp.com")


class GetEmployeeTests(unittest.IsolatedAsyncioTestCase):
    async def test_get_employee_not_found(self) -> None:
        svc = _service()
        with self.assertRaises(EmployeeNotFoundError):
            await svc.get_employee(FakeDb(), "EMPXXX")


class UpdateEmployeeTests(unittest.IsolatedAsyncioTestCase):
    async def test_update_employee_success(self) -> None:
        existing = make_employee(name="Old Name", role="agent")
        emp_repo = CapturingEmployeeRepository(initial=[existing])
        audit_repo = CapturingAuditRepository()
        svc = _service(emp_repo, audit_repo)

        updated = await svc.update_employee(
            FakeDb(),
            existing.employee_id,
            EmployeeUpdate(name="New Name"),
            actor_employee_id="EMP999",
        )
        self.assertEqual(updated.name, "New Name")

    async def test_update_employee_writes_diff_in_audit(self) -> None:
        existing = make_employee(name="Old Name", role="agent")
        emp_repo = CapturingEmployeeRepository(initial=[existing])
        audit_repo = CapturingAuditRepository()
        svc = _service(emp_repo, audit_repo)

        await svc.update_employee(
            FakeDb(),
            existing.employee_id,
            EmployeeUpdate(name="New Name", role="manager"),
            actor_employee_id="EMP999",
        )
        self.assertEqual(len(audit_repo.records), 1)
        log = audit_repo.records[0]
        self.assertEqual(log.action, "employee.updated")
        changes = log.details["changes"]
        self.assertIn("name", changes)
        self.assertEqual(changes["name"]["old_value"], "Old Name")
        self.assertEqual(changes["name"]["new_value"], "New Name")
        self.assertIn("role", changes)

    async def test_update_employee_email_conflict_raises(self) -> None:
        alice = make_employee(email="alice@x.com", employee_id="EMP001")
        bob = make_employee(email="bob@x.com", employee_id="EMP002")
        emp_repo = CapturingEmployeeRepository(initial=[alice, bob])
        svc = _service(emp_repo)

        with self.assertRaises(EmployeeEmailConflictError):
            await svc.update_employee(
                FakeDb(),
                alice.employee_id,
                EmployeeUpdate(email="bob@x.com"),
            )

    async def test_update_employee_noop_when_no_changes(self) -> None:
        existing = make_employee(name="Same Name")
        emp_repo = CapturingEmployeeRepository(initial=[existing])
        audit_repo = CapturingAuditRepository()
        svc = _service(emp_repo, audit_repo)

        result = await svc.update_employee(
            FakeDb(),
            existing.employee_id,
            EmployeeUpdate(name="Same Name"),
            actor_employee_id="EMP999",
        )
        # No audit log — nothing changed
        self.assertEqual(len(audit_repo.records), 0)
        self.assertEqual(result.name, "Same Name")


class DeleteEmployeeTests(unittest.IsolatedAsyncioTestCase):
    async def test_delete_inactive_employee_success(self) -> None:
        emp = make_employee(status="inactive")
        emp_repo = CapturingEmployeeRepository(initial=[emp])
        audit_repo = CapturingAuditRepository()
        svc = _service(emp_repo, audit_repo)

        await svc.delete_employee(FakeDb(), emp.employee_id, actor_employee_id="EMP999")
        self.assertEqual(len(emp_repo._store), 0)
        self.assertEqual(audit_repo.records[0].action, "employee.deleted")

    async def test_delete_active_employee_raises_conflict(self) -> None:
        emp = make_employee(status="active")
        emp_repo = CapturingEmployeeRepository(initial=[emp])
        svc = _service(emp_repo)

        with self.assertRaises(EmployeeNotInactiveError):
            await svc.delete_employee(FakeDb(), emp.employee_id)

    async def test_delete_suspended_employee_raises_conflict(self) -> None:
        emp = make_employee(status="suspended")
        emp_repo = CapturingEmployeeRepository(initial=[emp])
        svc = _service(emp_repo)

        with self.assertRaises(EmployeeNotInactiveError):
            await svc.delete_employee(FakeDb(), emp.employee_id)


class SuspendActivateTests(unittest.IsolatedAsyncioTestCase):
    async def test_suspend_employee_records_reason(self) -> None:
        emp = make_employee(status="active")
        emp_repo = CapturingEmployeeRepository(initial=[emp])
        audit_repo = CapturingAuditRepository()
        svc = _service(emp_repo, audit_repo)

        result = await svc.suspend_employee(
            FakeDb(), emp.employee_id, actor_employee_id="EMP999", reason="Policy violation"
        )
        self.assertEqual(result.status, "suspended")
        log = audit_repo.records[0]
        self.assertEqual(log.action, "employee.suspended")
        self.assertEqual(log.details["reason"], "Policy violation")

    async def test_suspend_already_suspended_raises_409(self) -> None:
        emp = make_employee(status="suspended")
        emp_repo = CapturingEmployeeRepository(initial=[emp])
        svc = _service(emp_repo)

        with self.assertRaises(EmployeeAlreadySuspendedError):
            await svc.suspend_employee(
                FakeDb(), emp.employee_id, actor_employee_id="EMP999", reason="duplicate"
            )

    async def test_activate_employee_success(self) -> None:
        emp = make_employee(status="suspended")
        emp_repo = CapturingEmployeeRepository(initial=[emp])
        audit_repo = CapturingAuditRepository()
        svc = _service(emp_repo, audit_repo)

        result = await svc.activate_employee(FakeDb(), emp.employee_id, actor_employee_id="EMP999")
        self.assertEqual(result.status, "active")

    async def test_activate_already_active_raises_409(self) -> None:
        emp = make_employee(status="active")
        emp_repo = CapturingEmployeeRepository(initial=[emp])
        svc = _service(emp_repo)

        with self.assertRaises(EmployeeAlreadyActiveError):
            await svc.activate_employee(FakeDb(), emp.employee_id, actor_employee_id="EMP999")


class ResetPasswordTests(unittest.IsolatedAsyncioTestCase):
    async def test_reset_password_sets_must_change_flag(self) -> None:
        emp = make_employee(must_change_password=False)
        emp_repo = CapturingEmployeeRepository(initial=[emp])
        audit_repo = CapturingAuditRepository()
        svc = _service(emp_repo, audit_repo)

        updated_emp, temp_pwd = await svc.reset_password(
            FakeDb(), emp.employee_id, actor_employee_id="EMP999"
        )
        self.assertTrue(updated_emp.must_change_password)
        self.assertEqual(len(temp_pwd), 12)
        # Temp password must NOT appear in audit log details
        log = audit_repo.records[0]
        self.assertNotIn(temp_pwd, str(log.details or ""))

    async def test_reset_password_hash_is_valid(self) -> None:
        emp = make_employee()
        emp_repo = CapturingEmployeeRepository(initial=[emp])
        svc = _service(emp_repo)

        updated_emp, temp_pwd = await svc.reset_password(
            FakeDb(), emp.employee_id, actor_employee_id="EMP999"
        )
        self.assertTrue(verify_password(temp_pwd, updated_emp.password_hash))


class ChangePasswordTests(unittest.IsolatedAsyncioTestCase):
    async def test_change_password_clears_must_change_flag(self) -> None:
        emp = make_employee(
            password_hash=hash_password("old-password"),
            must_change_password=True,
        )
        emp_repo = CapturingEmployeeRepository(initial=[emp])
        svc = _service(emp_repo)

        result = await svc.change_password(
            FakeDb(), emp.employee_id, "old-password", "new-password-secure"
        )
        self.assertFalse(result.must_change_password)
        self.assertTrue(verify_password("new-password-secure", result.password_hash))

    async def test_change_password_wrong_current_raises_error(self) -> None:
        emp = make_employee(password_hash=hash_password("correct-pass"))
        emp_repo = CapturingEmployeeRepository(initial=[emp])
        svc = _service(emp_repo)

        with self.assertRaises(InvalidCredentialsError):
            await svc.change_password(
                FakeDb(), emp.employee_id, "wrong-pass", "new-secure-pass"
            )


if __name__ == "__main__":
    unittest.main()
