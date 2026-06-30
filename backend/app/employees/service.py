import asyncio
import secrets
import string
from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import Any, Optional

import bcrypt
from sqlalchemy.ext.asyncio import AsyncSession

from app.employees.models import Employee, Department
from app.employees.repository import (
    AuditLogRepository,
    DepartmentRepository,
    EmployeeRepository,
)
from app.employees.schemas import (
    DepartmentCreate,
    DepartmentUpdate,
    EmployeeCreate,
    EmployeeUpdate,
)


# ─── Custom Exceptions ────────────────────────────────────────────────────────

class EmployeeNotFoundError(LookupError):
    pass

class EmployeeEmailConflictError(ValueError):
    pass

class EmployeeNotInactiveError(ValueError):
    """Raised when a hard-delete is attempted on a non-inactive employee."""
    pass

class EmployeeAlreadySuspendedError(ValueError):
    pass

class EmployeeAlreadyActiveError(ValueError):
    pass

class RoleChangeNotPermittedError(PermissionError):
    """Raised when a role assignment violates promotion rules or self-promotion guard."""
    pass

class InvalidReportsToError(ValueError):
    """Raised when a reports_to assignment violates hierarchy rules."""
    pass

class InvalidCredentialsError(ValueError):
    pass

class AccountSuspendedError(ValueError):
    pass

class DepartmentNotFoundError(LookupError):
    pass

class DepartmentConflictError(ValueError):
    pass

class DepartmentHasEmployeesError(ValueError):
    """Raised when a department that still has employees is being hard-deleted."""
    pass


# ─── Password helpers ─────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


def generate_temp_password(length: int = 12) -> str:
    """Generate a cryptographically-safe random temporary password."""
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


# ─── EmployeeService ──────────────────────────────────────────────────────────

class EmployeeService:
    def __init__(
        self,
        employee_repo: EmployeeRepository | None = None,
        audit_repo: AuditLogRepository | None = None,
    ) -> None:
        self.employee_repo = employee_repo or EmployeeRepository()
        self.audit_repo = audit_repo or AuditLogRepository()

    # ── helpers ───────────────────────────────────────────────────────────────

    async def _get_or_404(self, db: AsyncSession, employee_id: str) -> Employee:
        employee = await self.employee_repo.get_by_employee_id(db, employee_id)
        if employee is None:
            raise EmployeeNotFoundError(f"Employee '{employee_id}' not found.")
        return employee

    async def _write_audit(
        self,
        db: AsyncSession,
        *,
        action: str,
        actor_employee_id: Optional[str],
        target_id: str,
        target_employee_id: str,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        await self.audit_repo.create(
            db,
            actor_employee_id=actor_employee_id,
            action=action,
            target_type="employee",
            target_id=target_id,
            details=details or {"employee_id": target_employee_id},
        )

    # ── create ────────────────────────────────────────────────────────────────

    async def create_employee(
        self,
        db: AsyncSession,
        payload: EmployeeCreate,
        created_by: Optional[str] = None,
    ) -> Employee:
        existing = await self.employee_repo.get_by_email(db, payload.email)
        if existing is not None:
            raise EmployeeEmailConflictError(
                f"Employee with email '{payload.email}' already exists."
            )
        try:
            employee = await self.employee_repo.create(
                db,
                name=payload.name,
                email=payload.email,
                password_hash=hash_password(payload.password),
                role=payload.role,
                department_id=payload.department_id,
                reports_to=payload.reports_to,
                status="active",
                must_change_password=False,
                created_by=created_by,
            )
            await self.audit_repo.create(
                db,
                actor_employee_id=created_by,
                action="employee.created",
                target_type="employee",
                target_id=employee.id,
                details={"email": payload.email, "role": payload.role},
            )
            await db.commit()
            await db.refresh(employee)
            return employee
        except Exception:
            await db.rollback()
            raise

    # ── read ──────────────────────────────────────────────────────────────────

    async def get_employee(self, db: AsyncSession, employee_id: str) -> Employee:
        return await self._get_or_404(db, employee_id)

    async def list_employees(
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
        return await self.employee_repo.list(
            db,
            role=role,
            department_id=department_id,
            status=status,
            search=search,
            limit=limit,
            offset=offset,
        )

    # ── update ────────────────────────────────────────────────────────────────

    async def update_employee(
        self,
        db: AsyncSession,
        employee_id: str,
        payload: EmployeeUpdate,
        actor_employee_id: Optional[str] = None,
        actor_role: Optional[str] = None,
    ) -> Employee:
        employee = await self._get_or_404(db, employee_id)

        # ── Role-change guard rails ──────────────────────────────────────────
        # Evaluated before building the diff so they can never be bypassed.
        _ADMIN_LEVEL_ROLES = {"admin", "super_admin"}

        if payload.role is not None and payload.role != employee.role:
            # Guard 1: self-promotion is never allowed for any role
            if actor_employee_id == employee.employee_id:
                raise RoleChangeNotPermittedError("Cannot change your own role.")

            # Guard 2: only super_admin may promote someone to admin / super_admin
            if payload.role in _ADMIN_LEVEL_ROLES and actor_role != "super_admin":
                raise RoleChangeNotPermittedError(
                    "Only super_admin can assign admin-level roles."
                )

            # Guard 3: only super_admin may change the role of admin-level employees
            if employee.role in _ADMIN_LEVEL_ROLES and actor_role != "super_admin":
                raise RoleChangeNotPermittedError(
                    "Only super_admin can change the role of an admin-level employee."
                )

        # ── Reporting-chain validation ────────────────────────────────────────
        if payload.reports_to is not None:
            await self.validate_reports_to(db, employee.id, payload.reports_to)

        # Build diff of changed fields (old_value / new_value per field)
        UPDATABLE = ("name", "email", "role", "department_id", "reports_to")
        changes: dict[str, dict[str, Any]] = {}
        update_fields: dict[str, Any] = {}

        for field in UPDATABLE:
            new_val = getattr(payload, field, None)
            if new_val is None:
                continue
            old_val = getattr(employee, field, None)
            if old_val != new_val:
                changes[field] = {"old_value": old_val, "new_value": new_val}
                update_fields[field] = new_val

        # Email uniqueness check when email is being changed
        if "email" in update_fields:
            existing = await self.employee_repo.get_by_email(db, update_fields["email"])
            if existing is not None and existing.id != employee.id:
                raise EmployeeEmailConflictError(
                    f"Email '{update_fields['email']}' is already taken."
                )

        if not update_fields:
            # Nothing to change — return as-is
            return employee

        try:
            employee = await self.employee_repo.update(db, employee, **update_fields)
            await self._write_audit(
                db,
                action="employee.updated",
                actor_employee_id=actor_employee_id,
                target_id=employee.id,
                target_employee_id=employee_id,
                details={"changes": changes},
            )
            await db.commit()
            await db.refresh(employee)
            return employee
        except Exception:
            await db.rollback()
            raise

    # ── reporting-chain validation ─────────────────────────────────────────────

    async def validate_reports_to(
        self,
        db: AsyncSession,
        employee_id: str,
        new_reports_to_id: str,
    ) -> None:
        """Validate a reports_to assignment.

        Args:
            employee_id: The **id** (PK/UUID) of the employee being updated.
            new_reports_to_id: The **id** (PK/UUID) of the proposed manager.

        Raises:
            InvalidReportsToError: on self-report, invalid target role, or cycle.
        """
        # Rule 1: no self-report
        if new_reports_to_id == employee_id:
            raise InvalidReportsToError("Cannot set reports_to to self.")

        # Rule 2: target must be manager or higher
        _VALID_MANAGER_ROLES = {"manager", "admin", "super_admin"}
        target = await self.employee_repo.get(db, new_reports_to_id)
        if target is None or target.role not in _VALID_MANAGER_ROLES:
            raise InvalidReportsToError(
                "Reports-to target must be a manager or higher."
            )

        # Rule 3: cycle detection — walk the chain from target upward
        current_id = target.reports_to
        for _ in range(50):  # max 50 hops to avoid infinite loop on bad data
            if current_id is None:
                break
            if current_id == employee_id:
                raise InvalidReportsToError(
                    "This assignment would create a circular reporting structure."
                )
            ancestor = await self.employee_repo.get(db, current_id)
            if ancestor is None:
                break
            current_id = ancestor.reports_to

    # ── reassign ──────────────────────────────────────────────────────────────

    _UNSET = object()  # sentinel to distinguish "not provided" from None

    async def reassign_employee(
        self,
        db: AsyncSession,
        employee_id: str,
        *,
        department_id: Any = _UNSET,
        reports_to: Any = _UNSET,
        actor_employee_id: str,
    ) -> Employee:
        """Reassign an employee's department and/or reports_to.

        Only updates fields that are explicitly provided (not _UNSET).
        Writes a single 'employee.reassigned' audit log row.
        """
        employee = await self._get_or_404(db, employee_id)

        update_fields: dict[str, Any] = {}
        details: dict[str, Any] = {}

        if department_id is not self._UNSET:
            details["old_department_id"] = employee.department_id
            details["new_department_id"] = department_id
            if department_id != employee.department_id:
                update_fields["department_id"] = department_id

        if reports_to is not self._UNSET:
            if reports_to is not None:
                await self.validate_reports_to(db, employee.id, reports_to)
            details["old_reports_to"] = employee.reports_to
            details["new_reports_to"] = reports_to
            if reports_to != employee.reports_to:
                update_fields["reports_to"] = reports_to

        try:
            if update_fields:
                employee = await self.employee_repo.update(
                    db, employee, **update_fields
                )
            await self._write_audit(
                db,
                action="employee.reassigned",
                actor_employee_id=actor_employee_id,
                target_id=employee.id,
                target_employee_id=employee_id,
                details=details,
            )
            await db.commit()
            await db.refresh(employee)
            return employee
        except Exception:
            await db.rollback()
            raise

    # ── delete ────────────────────────────────────────────────────────────────

    async def delete_employee(
        self,
        db: AsyncSession,
        employee_id: str,
        actor_employee_id: Optional[str] = None,
    ) -> None:
        employee = await self._get_or_404(db, employee_id)
        if employee.status != "inactive":
            raise EmployeeNotInactiveError(
                "Employee must be deactivated before deletion."
            )
        try:
            await self._write_audit(
                db,
                action="employee.deleted",
                actor_employee_id=actor_employee_id,
                target_id=employee.id,
                target_employee_id=employee_id,
            )
            await self.employee_repo.delete(db, employee)
            await db.commit()
        except Exception:
            await db.rollback()
            raise

    # ── suspend / activate ────────────────────────────────────────────────────

    async def suspend_employee(
        self,
        db: AsyncSession,
        employee_id: str,
        actor_employee_id: str,
        reason: str,
    ) -> Employee:
        employee = await self._get_or_404(db, employee_id)
        if employee.status == "suspended":
            raise EmployeeAlreadySuspendedError(
                f"Employee '{employee_id}' is already suspended."
            )
        try:
            employee = await self.employee_repo.update(db, employee, status="suspended")
            await self._write_audit(
                db,
                action="employee.suspended",
                actor_employee_id=actor_employee_id,
                target_id=employee.id,
                target_employee_id=employee_id,
                details={"employee_id": employee_id, "reason": reason},
            )
            await db.commit()
            await db.refresh(employee)
            return employee
        except Exception:
            await db.rollback()
            raise

    async def activate_employee(
        self,
        db: AsyncSession,
        employee_id: str,
        actor_employee_id: str,
    ) -> Employee:
        employee = await self._get_or_404(db, employee_id)
        if employee.status == "active":
            raise EmployeeAlreadyActiveError(
                f"Employee '{employee_id}' is already active."
            )
        try:
            employee = await self.employee_repo.update(db, employee, status="active")
            await self._write_audit(
                db,
                action="employee.activated",
                actor_employee_id=actor_employee_id,
                target_id=employee.id,
                target_employee_id=employee_id,
            )
            await db.commit()
            await db.refresh(employee)
            return employee
        except Exception:
            await db.rollback()
            raise

    # ── lock / unlock ─────────────────────────────────────────────────────────

    async def lock_employee(
        self,
        db: AsyncSession,
        employee_id: str,
        actor_employee_id: str,
    ) -> Employee:
        employee = await self._get_or_404(db, employee_id)
        if employee.status == "suspended":
            raise EmployeeAlreadySuspendedError(
                f"Employee '{employee_id}' is already locked/suspended."
            )
        try:
            employee = await self.employee_repo.update(db, employee, status="suspended")
            await self._write_audit(
                db,
                action="employee.locked",
                actor_employee_id=actor_employee_id,
                target_id=employee.id,
                target_employee_id=employee_id,
                details={"employee_id": employee_id, "reason": "account_locked"},
            )
            await db.commit()
            await db.refresh(employee)
            return employee
        except Exception:
            await db.rollback()
            raise

    async def unlock_employee(
        self,
        db: AsyncSession,
        employee_id: str,
        actor_employee_id: str,
    ) -> Employee:
        employee = await self._get_or_404(db, employee_id)
        if employee.status == "active":
            raise EmployeeAlreadyActiveError(
                f"Employee '{employee_id}' is already active/unlocked."
            )
        try:
            employee = await self.employee_repo.update(db, employee, status="active")
            await self._write_audit(
                db,
                action="employee.unlocked",
                actor_employee_id=actor_employee_id,
                target_id=employee.id,
                target_employee_id=employee_id,
            )
            await db.commit()
            await db.refresh(employee)
            return employee
        except Exception:
            await db.rollback()
            raise

    # ── password management ───────────────────────────────────────────────────

    async def reset_password(
        self,
        db: AsyncSession,
        employee_id: str,
        actor_employee_id: str,
    ) -> tuple[Employee, str]:
        """Generate a temp password, hash it, set must_change_password=True.

        Returns ``(employee, temp_password)``. The plaintext temp_password is
        NEVER stored or logged — it is the caller's responsibility to return
        it exactly once in the API response.
        """
        employee = await self._get_or_404(db, employee_id)
        temp_password = generate_temp_password()
        try:
            employee = await self.employee_repo.update(
                db,
                employee,
                password_hash=hash_password(temp_password),
                must_change_password=True,
            )
            # Audit log must NOT contain the plaintext temp password
            await self._write_audit(
                db,
                action="employee.password_reset",
                actor_employee_id=actor_employee_id,
                target_id=employee.id,
                target_employee_id=employee_id,
            )
            await db.commit()
            await db.refresh(employee)
            return employee, temp_password
        except Exception:
            await db.rollback()
            raise

    async def change_password(
        self,
        db: AsyncSession,
        employee_id: str,
        current_password: str,
        new_password: str,
    ) -> Employee:
        """Verify current password then set the new one and clear must_change_password."""
        employee = await self._get_or_404(db, employee_id)
        if not verify_password(current_password, employee.password_hash):
            raise InvalidCredentialsError("Current password is incorrect.")
        try:
            employee = await self.employee_repo.update(
                db,
                employee,
                password_hash=hash_password(new_password),
                must_change_password=False,
            )
            await db.commit()
            await db.refresh(employee)
            return employee
        except Exception:
            await db.rollback()
            raise

    # ── auth ──────────────────────────────────────────────────────────────────

    async def authenticate(
        self,
        db: AsyncSession,
        email: str,
        password: str,
    ) -> Employee:
        employee = await self.employee_repo.get_by_email(db, email)
        if employee is None:
            await self.audit_repo.create(
                db,
                actor_employee_id=None,
                action="auth.login_failed",
                target_type="employee",
                target_id=None,
                details={"email": email, "reason": "user_not_found"},
            )
            await db.commit()
            raise InvalidCredentialsError("Invalid email or password.")

        if not verify_password(password, employee.password_hash):
            await self.audit_repo.create(
                db,
                actor_employee_id=employee.employee_id,
                action="auth.login_failed",
                target_type="employee",
                target_id=employee.id,
                details={"email": email, "reason": "incorrect_password"},
            )
            await db.commit()
            raise InvalidCredentialsError("Invalid email or password.")

        if employee.status != "active":
            await self.audit_repo.create(
                db,
                actor_employee_id=employee.employee_id,
                action="auth.login_failed",
                target_type="employee",
                target_id=employee.id,
                details={"email": email, "reason": f"account_status_{employee.status}"},
            )
            await db.commit()
            raise AccountSuspendedError(f"Account is {employee.status}.")

        try:
            await self.audit_repo.create(
                db,
                actor_employee_id=employee.employee_id,
                action="auth.login_success",
                target_type="employee",
                target_id=employee.id,
                details={"email": email},
            )
            await db.commit()
            await db.refresh(employee)
            return employee
        except Exception:
            await db.rollback()
            raise

    # ── audit log query ───────────────────────────────────────────────────────

    async def list_audit_logs(
        self,
        db: AsyncSession,
        *,
        actor_employee_id: Optional[str] = None,
        action: Optional[str] = None,
        action_prefix: Optional[str] = None,
        target_type: Optional[str] = None,
        date_from: Optional[Any] = None,
        date_to: Optional[Any] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        """Return audit log entries with actor_name resolved from Employee.

        Returns a list of dicts (not ORM objects) so the caller can pass them
        directly to response schemas.
        """
        items, total = await self.audit_repo.list(
            db,
            actor_employee_id=actor_employee_id,
            action=action,
            action_prefix=action_prefix,
            target_type=target_type,
            date_from=date_from,
            date_to=date_to,
            limit=limit,
            offset=offset,
        )

        # Batch-resolve actor_employee_id → actor_name
        actor_ids = {
            log.actor_employee_id
            for log in items
            if log.actor_employee_id is not None
        }
        name_map: dict[str, str] = {}
        for aid in actor_ids:
            emp = await self.employee_repo.get_by_employee_id(db, aid)
            if emp is not None:
                name_map[aid] = emp.name

        enriched: list[dict[str, Any]] = []
        for log in items:
            enriched.append({
                "id": log.id,
                "actor_employee_id": log.actor_employee_id,
                "actor_name": name_map.get(log.actor_employee_id) if log.actor_employee_id else None,
                "action": log.action,
                "target_type": log.target_type,
                "target_id": log.target_id,
                "details": log.details,
                "created_at": log.created_at,
            })

        return enriched, total

    # ── admin dashboard ───────────────────────────────────────────────────────

    async def get_dashboard_summary(
        self,
        db: AsyncSession,
    ) -> dict[str, Any]:
        """Compose an admin dashboard snapshot from existing repositories.

        Runs independent reads concurrently via ``asyncio.gather``.
        Complaint and SLA numbers use inline queries because the analytics
        and SLA modules operate on raw SQL with heavy aggregation functions
        that don't map cleanly to a simple count reuse.
        """

        async def _employee_counts() -> tuple[dict, dict]:
            all_employees, _total = await self.employee_repo.list(
                db, limit=10_000, offset=0
            )
            status_counts = Counter(e.status for e in all_employees)
            role_counts = Counter(e.role for e in all_employees)
            return (
                {
                    "total": len(all_employees),
                    "active": status_counts.get("active", 0),
                    "suspended": status_counts.get("suspended", 0),
                    "inactive": status_counts.get("inactive", 0),
                },
                dict(role_counts),
            )

        async def _department_count() -> int:
            from app.employees.repository import DepartmentRepository
            _depts, total = await DepartmentRepository().list(db, limit=1, offset=0)
            return total

        async def _recently_active() -> int:
            """Count distinct employees with auth.login_success in last 30 min."""
            cutoff = datetime.now(UTC) - timedelta(minutes=30)
            logs, _total = await self.audit_repo.list(
                db, action="auth.login_success", date_from=cutoff, limit=10_000,
            )
            return len({log.actor_employee_id for log in logs if log.actor_employee_id})

        async def _complaint_counts() -> dict[str, int]:
            """Inline minimal queries for complaint counts — reusing Complaint
            model directly because analytics repo functions return heavy
            aggregated payloads (timelines, heatmaps) unsuitable for simple
            counts."""
            from sqlalchemy import func, select, text as sa_text
            from app.models.complaint import Complaint

            today_start = datetime.now(UTC).replace(
                hour=0, minute=0, second=0, microsecond=0
            )

            # complaints_today
            today_count = (
                await db.execute(
                    select(func.count()).select_from(Complaint).where(
                        Complaint.created_at >= today_start
                    )
                )
            ).scalar_one()

            # open_complaints (ai_status = 'pending' or 'processing')
            open_count = (
                await db.execute(
                    select(func.count()).select_from(Complaint).where(
                        Complaint.ai_status.in_(["pending", "processing"])
                    )
                )
            ).scalar_one()

            # escalated_complaints (ai_status = 'human_review')
            escalated = (
                await db.execute(
                    select(func.count()).select_from(Complaint).where(
                        Complaint.ai_status == "human_review"
                    )
                )
            ).scalar_one()

            return {
                "complaints_today": today_count,
                "open_complaints": open_count,
                "escalated_complaints": escalated,
            }

        async def _sla_breaches_today() -> int:
            """Count SLA breaches (timely_response=false) received today."""
            from sqlalchemy import func, select
            from app.models.complaint import Complaint

            today_start = datetime.now(UTC).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            return (
                await db.execute(
                    select(func.count()).select_from(Complaint).where(
                        Complaint.date_received >= today_start,
                        Complaint.timely_response == False,  # noqa: E712
                    )
                )
            ).scalar_one()

        # Run all independent reads concurrently
        (
            (status_counts, role_counts),
            dept_count,
            recent_active,
            complaint_nums,
            sla_breach_count,
        ) = await asyncio.gather(
            _employee_counts(),
            _department_count(),
            _recently_active(),
            _complaint_counts(),
            _sla_breaches_today(),
        )

        return {
            "employee_counts": status_counts,
            "role_counts": role_counts,
            "department_count": dept_count,
            "recently_active_employees": recent_active,
            "complaints_today": complaint_nums["complaints_today"],
            "open_complaints": complaint_nums["open_complaints"],
            "escalated_complaints": complaint_nums["escalated_complaints"],
            "sla_breaches_today": sla_breach_count,
            "generated_at": datetime.now(UTC),
        }


# ─── DepartmentService ────────────────────────────────────────────────────────

class DepartmentService:
    def __init__(
        self,
        department_repo: DepartmentRepository | None = None,
        employee_repo: EmployeeRepository | None = None,
    ) -> None:
        self.department_repo = department_repo or DepartmentRepository()
        self.employee_repo = employee_repo or EmployeeRepository()

    async def create_department(self, db: AsyncSession, payload: DepartmentCreate) -> Department:
        if await self.department_repo.get_by_name(db, payload.name) is not None:
            raise DepartmentConflictError(
                f"Department name '{payload.name}' already exists."
            )
        if await self.department_repo.get_by_code(db, payload.code) is not None:
            raise DepartmentConflictError(
                f"Department code '{payload.code}' already exists."
            )
        try:
            department = await self.department_repo.create(
                db, name=payload.name, code=payload.code
            )
            await db.commit()
            await db.refresh(department)
            return department
        except Exception:
            await db.rollback()
            raise

    async def get_department(self, db: AsyncSession, department_id: str) -> Department:
        department = await self.department_repo.get(db, department_id)
        if department is None:
            raise DepartmentNotFoundError(f"Department '{department_id}' not found.")
        return department

    async def list_departments(
        self,
        db: AsyncSession,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[tuple[Department, int]], int]:
        """Return (department, employee_count) pairs with a single SQL query."""
        return await self.department_repo.list_with_counts(db, limit=limit, offset=offset)

    async def update_department(
        self,
        db: AsyncSession,
        department_id: str,
        payload: DepartmentUpdate,
    ) -> Department:
        department = await self.department_repo.get(db, department_id)
        if department is None:
            raise DepartmentNotFoundError(f"Department '{department_id}' not found.")

        if payload.name is not None:
            existing = await self.department_repo.get_by_name(db, payload.name)
            if existing is not None and existing.id != department_id:
                raise DepartmentConflictError(
                    f"Department name '{payload.name}' already exists."
                )
        if payload.code is not None:
            existing = await self.department_repo.get_by_code(db, payload.code)
            if existing is not None and existing.id != department_id:
                raise DepartmentConflictError(
                    f"Department code '{payload.code}' already exists."
                )

        fields: dict[str, Any] = {}
        if payload.name is not None:
            fields["name"] = payload.name
        if payload.code is not None:
            fields["code"] = payload.code

        if not fields:
            return department

        try:
            updated = await self.department_repo.update(db, department, **fields)
            await db.commit()
            await db.refresh(updated)
            return updated
        except Exception:
            await db.rollback()
            raise

    async def delete_department(self, db: AsyncSession, department_id: str) -> None:
        department = await self.department_repo.get(db, department_id)
        if department is None:
            raise DepartmentNotFoundError(f"Department '{department_id}' not found.")

        count = await self.employee_repo.count_by_department(db, department_id)
        if count > 0:
            raise DepartmentHasEmployeesError(
                f"Department '{department_id}' still has {count} employee(s). "
                "Reassign or remove them before deleting."
            )

        try:
            await self.department_repo.delete(db, department)
            await db.commit()
        except Exception:
            await db.rollback()
            raise
