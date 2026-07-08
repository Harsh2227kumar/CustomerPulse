from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.employees.models import AuditLog, Department, Employee



class EmployeeRepository:
    async def create(self, db: AsyncSession, **fields: Any) -> Employee:
        if "employee_id" not in fields or not fields["employee_id"]:
            res = await db.execute(text("SELECT nextval('employee_id_seq')"))
            val = res.scalar()
            fields["employee_id"] = f"EMP{val:03d}"

        employee = Employee(**fields)
        db.add(employee)
        await db.flush()
        return employee

    async def get(self, db: AsyncSession, pk: str) -> Employee | None:
        """Fetch by primary-key UUID (the ``id`` column)."""
        return await db.get(Employee, pk)

    async def get_by_email(self, db: AsyncSession, email: str) -> Employee | None:
        stmt = select(Employee).where(Employee.email == email)
        return (await db.execute(stmt)).scalar_one_or_none()

    async def get_by_employee_id(self, db: AsyncSession, employee_id: str) -> Employee | None:
        """Fetch by the ``employee_id`` business key (e.g. ``EMP001``)."""
        stmt = select(Employee).where(Employee.employee_id == employee_id)
        return (await db.execute(stmt)).scalar_one_or_none()

    async def list(
        self,
        db: AsyncSession,
        *,
        role: Optional[str] = None,
        department_id: Optional[str] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Employee], int]:
        stmt = select(Employee)
        count_stmt = select(func.count()).select_from(Employee)

        if role is not None:
            stmt = stmt.where(Employee.role == role)
            count_stmt = count_stmt.where(Employee.role == role)
        if department_id is not None:
            stmt = stmt.where(Employee.department_id == department_id)
            count_stmt = count_stmt.where(Employee.department_id == department_id)
        if status is not None:
            stmt = stmt.where(Employee.status == status)
            count_stmt = count_stmt.where(Employee.status == status)
        if search is not None:
            pattern = f"%{search}%"
            search_filter = or_(
                Employee.name.ilike(pattern),
                Employee.email.ilike(pattern),
            )
            stmt = stmt.where(search_filter)
            count_stmt = count_stmt.where(search_filter)

        total = (await db.execute(count_stmt)).scalar_one()
        stmt = stmt.order_by(Employee.created_at.desc()).limit(limit).offset(offset)
        items = (await db.execute(stmt)).scalars().all()
        return list(items), total

    async def update(self, db: AsyncSession, employee: Employee, **fields: Any) -> Employee:
        for k, v in fields.items():
            if hasattr(employee, k):
                setattr(employee, k, v)
        await db.flush()
        return employee

    async def count_by_department(self, db: AsyncSession, department_id: str) -> int:
        """Return the number of employees referencing this department."""
        stmt = select(func.count()).select_from(Employee).where(
            Employee.department_id == department_id
        )
        return (await db.execute(stmt)).scalar_one()

    async def delete(self, db: AsyncSession, employee: Employee) -> None:
        await db.delete(employee)
        await db.flush()


class DepartmentRepository:
    async def create(self, db: AsyncSession, **fields: Any) -> Department:
        department = Department(**fields)
        db.add(department)
        await db.flush()
        return department

    async def get(self, db: AsyncSession, department_id: str) -> Department | None:
        return await db.get(Department, department_id)

    async def get_by_name(self, db: AsyncSession, name: str) -> Department | None:
        stmt = select(Department).where(Department.name == name)
        return (await db.execute(stmt)).scalar_one_or_none()

    async def get_by_code(self, db: AsyncSession, code: str) -> Department | None:
        stmt = select(Department).where(Department.code == code)
        return (await db.execute(stmt)).scalar_one_or_none()

    async def list(
        self,
        db: AsyncSession,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Department], int]:
        stmt = select(Department)
        count_stmt = select(func.count()).select_from(Department)

        total = (await db.execute(count_stmt)).scalar_one()
        stmt = stmt.order_by(Department.name.asc()).limit(limit).offset(offset)
        items = (await db.execute(stmt)).scalars().all()
        return list(items), total

    async def list_with_counts(
        self,
        db: AsyncSession,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[tuple[Department, int]], int]:
        """Return departments paired with their employee count in a single query."""
        # Subquery: count employees per department
        emp_count_sq = (
            select(
                Employee.department_id.label("dept_id"),
                func.count(Employee.id).label("emp_count"),
            )
            .group_by(Employee.department_id)
            .subquery()
        )

        stmt = (
            select(Department, func.coalesce(emp_count_sq.c.emp_count, 0).label("employee_count"))
            .outerjoin(emp_count_sq, Department.id == emp_count_sq.c.dept_id)
            .order_by(Department.name.asc())
        )
        count_stmt = select(func.count()).select_from(Department)
        total = (await db.execute(count_stmt)).scalar_one()

        paginated = stmt.limit(limit).offset(offset)
        rows = (await db.execute(paginated)).all()
        return [(row[0], row[1]) for row in rows], total

    async def update(self, db: AsyncSession, department: Department, **fields: Any) -> Department:
        for k, v in fields.items():
            if hasattr(department, k):
                setattr(department, k, v)
        await db.flush()
        return department

    async def delete(self, db: AsyncSession, department: Department) -> None:
        await db.delete(department)
        await db.flush()


class AuditLogRepository:
    async def create(self, db: AsyncSession, **fields: Any) -> AuditLog:
        audit_log = AuditLog(**fields)
        db.add(audit_log)
        await db.flush()
        return audit_log

    async def list(
        self,
        db: AsyncSession,
        *,
        actor_employee_id: Optional[str] = None,
        action: Optional[str] = None,
        action_prefix: Optional[str] = None,
        target_type: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[AuditLog], int]:
        stmt = select(AuditLog)
        count_stmt = select(func.count()).select_from(AuditLog)

        if actor_employee_id is not None:
            stmt = stmt.where(AuditLog.actor_employee_id == actor_employee_id)
            count_stmt = count_stmt.where(AuditLog.actor_employee_id == actor_employee_id)
        if action is not None:
            stmt = stmt.where(AuditLog.action == action)
            count_stmt = count_stmt.where(AuditLog.action == action)
        elif action_prefix is not None:
            like_pattern = f"{action_prefix}%"
            stmt = stmt.where(AuditLog.action.like(like_pattern))
            count_stmt = count_stmt.where(AuditLog.action.like(like_pattern))
        if target_type is not None:
            stmt = stmt.where(AuditLog.target_type == target_type)
            count_stmt = count_stmt.where(AuditLog.target_type == target_type)
        if date_from is not None:
            stmt = stmt.where(AuditLog.created_at >= date_from)
            count_stmt = count_stmt.where(AuditLog.created_at >= date_from)
        if date_to is not None:
            stmt = stmt.where(AuditLog.created_at <= date_to)
            count_stmt = count_stmt.where(AuditLog.created_at <= date_to)

        total = (await db.execute(count_stmt)).scalar_one()
        stmt = stmt.order_by(AuditLog.created_at.desc()).limit(limit).offset(offset)
        items = (await db.execute(stmt)).scalars().all()
        return list(items), total

