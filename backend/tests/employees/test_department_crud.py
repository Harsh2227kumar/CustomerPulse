"""Service-level unit tests for department CRUD operations."""
import os
import sys
import unittest

os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost/test")
os.environ.setdefault("BEDROCK_API_KEY", "test-key")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from tests.employees.conftest import (
    CapturingAuditRepository,
    CapturingDepartmentRepository,
    CapturingEmployeeRepository,
    FakeDb,
    make_department,
    make_employee,
)
from app.employees.schemas import DepartmentCreate, DepartmentUpdate
from app.employees.service import (
    DepartmentConflictError,
    DepartmentHasEmployeesError,
    DepartmentNotFoundError,
    DepartmentService,
)


def _svc(dept_repo=None, emp_repo=None) -> DepartmentService:
    return DepartmentService(
        department_repo=dept_repo or CapturingDepartmentRepository(),
        employee_repo=emp_repo or CapturingEmployeeRepository(),
    )


class CreateDepartmentTests(unittest.IsolatedAsyncioTestCase):
    async def test_create_department_success(self) -> None:
        svc = _svc()
        dept = await svc.create_department(
            FakeDb(), DepartmentCreate(name="Operations", code="OPS")
        )
        self.assertEqual(dept.name, "Operations")
        self.assertEqual(dept.code, "OPS")

    async def test_create_department_name_conflict(self) -> None:
        existing = make_department(name="Operations", code="OPS")
        svc = _svc(CapturingDepartmentRepository(initial=[existing]))

        with self.assertRaises(DepartmentConflictError):
            await svc.create_department(
                FakeDb(), DepartmentCreate(name="Operations", code="OPS2")
            )

    async def test_create_department_code_conflict(self) -> None:
        existing = make_department(name="Operations", code="OPS")
        svc = _svc(CapturingDepartmentRepository(initial=[existing]))

        with self.assertRaises(DepartmentConflictError):
            await svc.create_department(
                FakeDb(), DepartmentCreate(name="Operations 2", code="OPS")
            )


class ListDepartmentsTests(unittest.IsolatedAsyncioTestCase):
    async def test_list_departments_returns_employee_count(self) -> None:
        dept1 = make_department(name="Alpha", code="A")
        dept2 = make_department(name="Beta", code="B")
        dept_repo = CapturingDepartmentRepository(initial=[dept1, dept2])
        emp_repo = CapturingEmployeeRepository(initial=[
            make_employee(department_id=dept1.id, employee_id="EMP001"),
            make_employee(department_id=dept1.id, employee_id="EMP002", email="e2@x.com"),
        ])

        # Manually call list_with_counts as the service delegates to it
        rows, total = await dept_repo.list_with_counts(
            FakeDb(), employee_repo=emp_repo
        )
        dept_by_name = {dept.name: count for dept, count in rows}
        self.assertEqual(dept_by_name["Alpha"], 2)
        self.assertEqual(dept_by_name["Beta"], 0)
        self.assertEqual(total, 2)

    async def test_list_departments_pagination(self) -> None:
        depts = [make_department(name=f"Dept{i}", code=f"D{i}") for i in range(5)]
        dept_repo = CapturingDepartmentRepository(initial=depts)
        svc = _svc(dept_repo)

        rows, total = await svc.list_departments(FakeDb(), limit=2, offset=0)
        self.assertEqual(total, 5)
        self.assertEqual(len(rows), 2)


class UpdateDepartmentTests(unittest.IsolatedAsyncioTestCase):
    async def test_update_department_name(self) -> None:
        dept = make_department(name="Old Name", code="OLD")
        dept_repo = CapturingDepartmentRepository(initial=[dept])
        svc = _svc(dept_repo)

        updated = await svc.update_department(
            FakeDb(), dept.id, DepartmentUpdate(name="New Name")
        )
        self.assertEqual(updated.name, "New Name")

    async def test_update_department_name_conflict(self) -> None:
        dept1 = make_department(name="Alpha", code="A")
        dept2 = make_department(name="Beta", code="B")
        dept_repo = CapturingDepartmentRepository(initial=[dept1, dept2])
        svc = _svc(dept_repo)

        with self.assertRaises(DepartmentConflictError):
            await svc.update_department(
                FakeDb(), dept1.id, DepartmentUpdate(name="Beta")
            )

    async def test_update_department_not_found(self) -> None:
        svc = _svc()
        with self.assertRaises(DepartmentNotFoundError):
            await svc.update_department(
                FakeDb(), "nonexistent-id", DepartmentUpdate(name="X")
            )

    async def test_update_department_noop_returns_unchanged(self) -> None:
        dept = make_department(name="Alpha", code="A")
        dept_repo = CapturingDepartmentRepository(initial=[dept])
        svc = _svc(dept_repo)

        result = await svc.update_department(FakeDb(), dept.id, DepartmentUpdate())
        self.assertEqual(result.name, "Alpha")


class DeleteDepartmentTests(unittest.IsolatedAsyncioTestCase):
    async def test_delete_empty_department_success(self) -> None:
        dept = make_department()
        dept_repo = CapturingDepartmentRepository(initial=[dept])
        svc = _svc(dept_repo)

        await svc.delete_department(FakeDb(), dept.id)
        self.assertEqual(len(dept_repo._store), 0)

    async def test_delete_department_with_employees_raises_409(self) -> None:
        dept = make_department()
        emp = make_employee(department_id=dept.id)
        dept_repo = CapturingDepartmentRepository(initial=[dept])
        emp_repo = CapturingEmployeeRepository(initial=[emp])
        svc = _svc(dept_repo, emp_repo)

        with self.assertRaises(DepartmentHasEmployeesError):
            await svc.delete_department(FakeDb(), dept.id)

    async def test_delete_nonexistent_department_raises_404(self) -> None:
        svc = _svc()
        with self.assertRaises(DepartmentNotFoundError):
            await svc.delete_department(FakeDb(), "bad-id")


if __name__ == "__main__":
    unittest.main()
