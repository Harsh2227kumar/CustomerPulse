"""Shared in-memory fakes for employee tests.

These capturing repositories hold data in Python lists/dicts so tests never
touch the database. The pattern mirrors tests/compliance/conftest.py.
"""
from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any, Optional
from uuid import uuid4


# ─── Fake domain objects ──────────────────────────────────────────────────────

def make_department(**overrides: Any) -> SimpleNamespace:
    now = datetime.now(UTC)
    defaults = {
        "id": str(uuid4()),
        "name": "Loans",
        "code": "LOANS",
        "created_at": now,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def make_employee(**overrides: Any) -> SimpleNamespace:
    from app.employees.service import hash_password

    now = datetime.now(UTC)
    defaults = {
        "id": str(uuid4()),
        "employee_id": "EMP001",
        "name": "Jane Doe",
        "email": "jane@example.com",
        "password_hash": hash_password("password123"),
        "role": "agent",
        "department_id": None,
        "reports_to": None,
        "status": "active",
        "must_change_password": False,
        "created_at": now,
        "updated_at": now,
        "created_by": None,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def make_audit_log(**overrides: Any) -> SimpleNamespace:
    defaults = {
        "id": str(uuid4()),
        "actor_employee_id": None,
        "action": "employee.created",
        "target_type": "employee",
        "target_id": None,
        "details": {},
        "created_at": datetime.now(UTC),
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


# ─── Capturing repositories ───────────────────────────────────────────────────

class CapturingEmployeeRepository:
    """In-memory EmployeeRepository substitute for unit tests."""

    def __init__(self, initial: list[Any] | None = None) -> None:
        self._store: list[Any] = list(initial or [])
        self._seq: int = 1

    async def create(self, db: Any, **fields: Any) -> Any:
        if "employee_id" not in fields or not fields["employee_id"]:
            fields["employee_id"] = f"EMP{self._seq:03d}"
            self._seq += 1
        if "id" not in fields:
            fields["id"] = str(uuid4())
        now = datetime.now(UTC)
        fields.setdefault("created_at", now)
        fields.setdefault("updated_at", now)
        fields.setdefault("status", "active")
        fields.setdefault("must_change_password", False)
        obj = SimpleNamespace(**fields)
        self._store.append(obj)
        return obj

    async def get(self, db: Any, pk: str) -> Any | None:
        return next((e for e in self._store if e.id == pk), None)

    async def get_by_email(self, db: Any, email: str) -> Any | None:
        return next((e for e in self._store if e.email == email), None)

    async def get_by_employee_id(self, db: Any, employee_id: str) -> Any | None:
        return next((e for e in self._store if e.employee_id == employee_id), None)

    async def list(
        self,
        db: Any,
        *,
        role: Optional[str] = None,
        department_id: Optional[str] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Any], int]:
        items = list(self._store)
        if role is not None:
            items = [e for e in items if e.role == role]
        if department_id is not None:
            items = [e for e in items if e.department_id == department_id]
        if status is not None:
            items = [e for e in items if e.status == status]
        if search is not None:
            low = search.lower()
            items = [
                e for e in items
                if low in e.name.lower() or low in e.email.lower()
            ]
        total = len(items)
        return items[offset: offset + limit], total

    async def update(self, db: Any, employee: Any, **fields: Any) -> Any:
        for k, v in fields.items():
            setattr(employee, k, v)
        employee.updated_at = datetime.now(UTC)
        return employee

    async def count_by_department(self, db: Any, department_id: str) -> int:
        return sum(1 for e in self._store if e.department_id == department_id)

    async def delete(self, db: Any, employee: Any) -> None:
        self._store = [e for e in self._store if e.id != employee.id]


class CapturingAuditRepository:
    """In-memory AuditLogRepository substitute for unit tests."""

    def __init__(self) -> None:
        self.records: list[Any] = []

    async def create(self, db: Any, **fields: Any) -> Any:
        fields.setdefault("id", str(uuid4()))
        fields.setdefault("created_at", datetime.now(UTC))
        obj = SimpleNamespace(**fields)
        self.records.append(obj)
        return obj

    async def list(
        self,
        db: Any,
        *,
        actor_employee_id: Optional[str] = None,
        action: Optional[str] = None,
        action_prefix: Optional[str] = None,
        target_type: Optional[str] = None,
        date_from: Any = None,
        date_to: Any = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Any], int]:
        items = list(self.records)
        if actor_employee_id is not None:
            items = [r for r in items if getattr(r, "actor_employee_id", None) == actor_employee_id]
        if action is not None:
            items = [r for r in items if getattr(r, "action", None) == action]
        elif action_prefix is not None:
            items = [r for r in items if getattr(r, "action", "").startswith(action_prefix)]
        if target_type is not None:
            items = [r for r in items if getattr(r, "target_type", None) == target_type]
        if date_from is not None:
            items = [r for r in items if getattr(r, "created_at", None) is not None and r.created_at >= date_from]
        if date_to is not None:
            items = [r for r in items if getattr(r, "created_at", None) is not None and r.created_at <= date_to]
        total = len(items)
        return items[offset: offset + limit], total


class CapturingDepartmentRepository:
    """In-memory DepartmentRepository substitute for unit tests."""

    def __init__(self, initial: list[Any] | None = None) -> None:
        self._store: list[Any] = list(initial or [])

    async def create(self, db: Any, **fields: Any) -> Any:
        fields.setdefault("id", str(uuid4()))
        fields.setdefault("created_at", datetime.now(UTC))
        obj = SimpleNamespace(**fields)
        self._store.append(obj)
        return obj

    async def get(self, db: Any, department_id: str) -> Any | None:
        return next((d for d in self._store if d.id == department_id), None)

    async def get_by_name(self, db: Any, name: str) -> Any | None:
        return next((d for d in self._store if d.name == name), None)

    async def get_by_code(self, db: Any, code: str) -> Any | None:
        return next((d for d in self._store if d.code == code), None)

    async def list(
        self, db: Any, *, limit: int = 50, offset: int = 0
    ) -> tuple[list[Any], int]:
        items = sorted(self._store, key=lambda d: d.name)
        total = len(items)
        return items[offset: offset + limit], total

    async def list_with_counts(
        self,
        db: Any,
        *,
        limit: int = 50,
        offset: int = 0,
        employee_repo: Optional[CapturingEmployeeRepository] = None,
    ) -> tuple[list[tuple[Any, int]], int]:
        items = sorted(self._store, key=lambda d: d.name)
        total = len(items)
        page = items[offset: offset + limit]
        if employee_repo is not None:
            counts = [
                (dept, sum(1 for e in employee_repo._store if e.department_id == dept.id))
                for dept in page
            ]
        else:
            counts = [(dept, 0) for dept in page]
        return counts, total

    async def update(self, db: Any, department: Any, **fields: Any) -> Any:
        for k, v in fields.items():
            setattr(department, k, v)
        return department

    async def delete(self, db: Any, department: Any) -> None:
        self._store = [d for d in self._store if d.id != department.id]


# ─── Fake async session ───────────────────────────────────────────────────────

class FakeDb:
    """Minimal async session double — tracks commit/rollback calls."""

    def __init__(self) -> None:
        self.committed = False
        self.rolled_back = False

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True

    async def refresh(self, _obj: Any) -> None:
        pass
