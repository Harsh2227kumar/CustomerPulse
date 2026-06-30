"""Employee, department, auth and me routers.

Pattern: catch domain exceptions from service → map to HTTP status codes.
Reference: app/escalations/router.py
"""
import secrets
import string
from datetime import UTC, datetime, timedelta
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.constants import Role
from app.core.security import create_jwt_token, get_current_principal, require_roles
from app.db.session import get_db_session
from app.employees.schemas import (
    AdminDashboardResponse,
    AuditLogEntry,
    AuditLogListResponse,
    ChangePasswordRequest,
    DepartmentCreate,
    DepartmentListResponse,
    DepartmentRead,
    DepartmentUpdate,
    DepartmentWithCount,
    EmployeeAssignRequest,
    EmployeeCreate,
    EmployeeListResponse,
    EmployeeRead,
    EmployeeUpdate,
    LoginHistoryEntry,
    LoginHistoryListResponse,
    LoginRequest,
    LoginResponse,
    ResetPasswordResponse,
    SuspendRequest,
)
from app.employees.permissions import all_roles_map, capabilities_for
from app.employees.service import (
    AccountSuspendedError,
    DepartmentConflictError,
    DepartmentHasEmployeesError,
    DepartmentNotFoundError,
    DepartmentService,
    EmployeeAlreadyActiveError,
    EmployeeAlreadySuspendedError,
    EmployeeEmailConflictError,
    EmployeeNotFoundError,
    EmployeeNotInactiveError,
    EmployeeService,
    InvalidCredentialsError,
    InvalidReportsToError,
    RoleChangeNotPermittedError,
)

auth_router = APIRouter(prefix="/api/auth", tags=["auth"])
admin_router = APIRouter(prefix="/api/admin", tags=["admin"])
me_router = APIRouter(prefix="/api/me", tags=["me"])


# ─── Auth ─────────────────────────────────────────────────────────────────────

@auth_router.post("/login", response_model=LoginResponse)
async def login(
    body: LoginRequest,
    settings: Annotated[Settings, Depends(get_settings)],
    db: AsyncSession = Depends(get_db_session),
) -> LoginResponse:
    try:
        employee = await EmployeeService().authenticate(db, body.email, body.password)
        payload = {
            "sub": employee.employee_id,
            "role": employee.role,
            "exp": (
                datetime.now(UTC) + timedelta(hours=settings.jwt_expiry_hours)
            ).timestamp(),
        }
        token = create_jwt_token(payload, settings.jwt_secret_key)
        return LoginResponse(
            access_token=token,
            role=employee.role,
            employee_id=employee.employee_id,
            must_change_password=employee.must_change_password,
        )
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        ) from exc
    except AccountSuspendedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc


# ─── Me ───────────────────────────────────────────────────────────────────────

@me_router.put("/change-password", response_model=EmployeeRead)
async def change_password(
    body: ChangePasswordRequest,
    principal=Depends(get_current_principal),
    db: AsyncSession = Depends(get_db_session),
) -> EmployeeRead:
    """Available to any authenticated employee.  Clears must_change_password flag."""
    try:
        employee = await EmployeeService().change_password(
            db,
            employee_id=principal.actor,
            current_password=body.current_password,
            new_password=body.new_password,
        )
        return EmployeeRead.model_validate(employee)
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect.",
        ) from exc
    except EmployeeNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

@admin_router.get("/roles")
async def list_roles(
    principal=Depends(get_current_principal),
) -> dict:
    """Returns the static ROLE_CAPABILITIES map plus the caller's own resolved capabilities."""
    return {
        "all_roles": all_roles_map(),
        "your_role": principal.role.value,
        "your_capabilities": capabilities_for(principal.role),
    }


# ─── Admin — Dashboard ────────────────────────────────────────────────────────

@admin_router.get("/dashboard", response_model=AdminDashboardResponse)
async def admin_dashboard(
    _principal=Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN)),
    db: AsyncSession = Depends(get_db_session),
) -> AdminDashboardResponse:
    """Aggregated dashboard snapshot — pure read, no audit log entry."""
    data = await EmployeeService().get_dashboard_summary(db)
    return AdminDashboardResponse(**data)


@admin_router.post(
    "/employees",
    response_model=EmployeeRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_employee(
    body: EmployeeCreate,
    principal=Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN)),
    db: AsyncSession = Depends(get_db_session),
) -> EmployeeRead:
    try:
        employee = await EmployeeService().create_employee(
            db, body, created_by=principal.actor
        )
        return EmployeeRead.model_validate(employee)
    except EmployeeEmailConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@admin_router.get("/employees", response_model=EmployeeListResponse)
async def list_employees(
    role: Optional[str] = Query(None),
    department_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None, description="Case-insensitive match on name or email"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _principal=Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN)),
    db: AsyncSession = Depends(get_db_session),
) -> EmployeeListResponse:
    items, total = await EmployeeService().list_employees(
        db,
        role=role,
        department_id=department_id,
        status=status,
        search=search,
        limit=limit,
        offset=offset,
    )
    return EmployeeListResponse(
        items=[EmployeeRead.model_validate(e) for e in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@admin_router.get("/employees/{employee_id}", response_model=EmployeeRead)
async def get_employee(
    employee_id: str,
    _principal=Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN)),
    db: AsyncSession = Depends(get_db_session),
) -> EmployeeRead:
    try:
        employee = await EmployeeService().get_employee(db, employee_id)
        return EmployeeRead.model_validate(employee)
    except EmployeeNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@admin_router.patch("/employees/{employee_id}", response_model=EmployeeRead)
async def update_employee(
    employee_id: str,
    body: EmployeeUpdate,
    principal=Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN)),
    db: AsyncSession = Depends(get_db_session),
) -> EmployeeRead:
    try:
        employee = await EmployeeService().update_employee(
            db, employee_id, body,
            actor_employee_id=principal.actor,
            actor_role=principal.role.value,
        )
        return EmployeeRead.model_validate(employee)
    except RoleChangeNotPermittedError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except InvalidReportsToError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except EmployeeNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except EmployeeEmailConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@admin_router.post("/employees/{employee_id}/assign", response_model=EmployeeRead)
async def assign_employee(
    employee_id: str,
    body: EmployeeAssignRequest,
    principal=Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN)),
    db: AsyncSession = Depends(get_db_session),
) -> EmployeeRead:
    """Reassign an employee's department and/or manager."""
    svc = EmployeeService()
    kwargs: dict = {"actor_employee_id": principal.actor}
    if body.department_id is not None:
        kwargs["department_id"] = body.department_id
    if body.reports_to is not None:
        kwargs["reports_to"] = body.reports_to
    try:
        employee = await svc.reassign_employee(db, employee_id, **kwargs)
        return EmployeeRead.model_validate(employee)
    except InvalidReportsToError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except EmployeeNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@admin_router.delete(
    "/employees/{employee_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_employee(
    employee_id: str,
    principal=Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN)),
    db: AsyncSession = Depends(get_db_session),
) -> None:
    try:
        await EmployeeService().delete_employee(
            db, employee_id, actor_employee_id=principal.actor
        )
    except EmployeeNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except EmployeeNotInactiveError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@admin_router.post("/employees/{employee_id}/suspend", response_model=EmployeeRead)
async def suspend_employee(
    employee_id: str,
    body: SuspendRequest,
    principal=Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN)),
    db: AsyncSession = Depends(get_db_session),
) -> EmployeeRead:
    try:
        employee = await EmployeeService().suspend_employee(
            db, employee_id, actor_employee_id=principal.actor, reason=body.reason
        )
        return EmployeeRead.model_validate(employee)
    except EmployeeNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except EmployeeAlreadySuspendedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@admin_router.post("/employees/{employee_id}/activate", response_model=EmployeeRead)
async def activate_employee(
    employee_id: str,
    principal=Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN)),
    db: AsyncSession = Depends(get_db_session),
) -> EmployeeRead:
    try:
        employee = await EmployeeService().activate_employee(
            db, employee_id, actor_employee_id=principal.actor
        )
        return EmployeeRead.model_validate(employee)
    except EmployeeNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except EmployeeAlreadyActiveError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@admin_router.post(
    "/employees/{employee_id}/reset-password",
    response_model=ResetPasswordResponse,
)
async def reset_password(
    employee_id: str,
    principal=Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN)),
    db: AsyncSession = Depends(get_db_session),
) -> ResetPasswordResponse:
    try:
        _employee, temp_password = await EmployeeService().reset_password(
            db, employee_id, actor_employee_id=principal.actor
        )
        # Return the temp password exactly once — it is never stored or logged
        return ResetPasswordResponse(temporary_password=temp_password)
    except EmployeeNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@admin_router.post("/employees/{employee_id}/lock", response_model=EmployeeRead)
async def lock_employee(
    employee_id: str,
    principal=Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN)),
    db: AsyncSession = Depends(get_db_session),
) -> EmployeeRead:
    try:
        employee = await EmployeeService().lock_employee(
            db, employee_id, actor_employee_id=principal.actor
        )
        return EmployeeRead.model_validate(employee)
    except EmployeeNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except EmployeeAlreadySuspendedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@admin_router.post("/employees/{employee_id}/unlock", response_model=EmployeeRead)
async def unlock_employee(
    employee_id: str,
    principal=Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN)),
    db: AsyncSession = Depends(get_db_session),
) -> EmployeeRead:
    try:
        employee = await EmployeeService().unlock_employee(
            db, employee_id, actor_employee_id=principal.actor
        )
        return EmployeeRead.model_validate(employee)
    except EmployeeNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except EmployeeAlreadyActiveError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


# ─── Admin — Departments ──────────────────────────────────────────────────────

@admin_router.post(
    "/departments",
    response_model=DepartmentRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_department(
    body: DepartmentCreate,
    _principal=Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN)),
    db: AsyncSession = Depends(get_db_session),
) -> DepartmentRead:
    try:
        department = await DepartmentService().create_department(db, body)
        return DepartmentRead.model_validate(department)
    except DepartmentConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@admin_router.get("/departments", response_model=DepartmentListResponse)
async def list_departments(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _principal=Depends(get_current_principal),   # any authenticated role
    db: AsyncSession = Depends(get_db_session),
) -> DepartmentListResponse:
    rows, total = await DepartmentService().list_departments(db, limit=limit, offset=offset)
    items = [
        DepartmentWithCount(
            id=dept.id,
            name=dept.name,
            code=dept.code,
            created_at=dept.created_at,
            employee_count=count,
        )
        for dept, count in rows
    ]
    return DepartmentListResponse(items=items, total=total, limit=limit, offset=offset)


@admin_router.patch("/departments/{department_id}", response_model=DepartmentRead)
async def update_department(
    department_id: str,
    body: DepartmentUpdate,
    _principal=Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN)),
    db: AsyncSession = Depends(get_db_session),
) -> DepartmentRead:
    try:
        department = await DepartmentService().update_department(db, department_id, body)
        return DepartmentRead.model_validate(department)
    except DepartmentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except DepartmentConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@admin_router.delete(
    "/departments/{department_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_department(
    department_id: str,
    _principal=Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN)),
    db: AsyncSession = Depends(get_db_session),
) -> None:
    try:
        await DepartmentService().delete_department(db, department_id)
    except DepartmentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except DepartmentHasEmployeesError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


# ─── Admin — Complaint Monitoring ─────────────────────────────────────────────

from app.employees.monitoring_schemas import ComplaintMonitoringResponse

@admin_router.get("/complaint-monitoring", response_model=ComplaintMonitoringResponse)
async def get_complaint_monitoring(
    _principal=Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN)),
    db: AsyncSession = Depends(get_db_session),
) -> ComplaintMonitoringResponse:
    from app.operations.repository import OperationsRepository
    from app.operations.schemas import OperationsQueueItem, OperationsQueueResponse
    from app.sla.services.sla_service import SLAService
    from app.sla.schemas.sla_schemas import SLASummaryQuery
    from app.escalations.repository import EscalationRepository
    from datetime import datetime, UTC
    
    # 1. Operations Queue
    items, total = await OperationsRepository().get_queue(db, limit=100, offset=0)
    ops_queue = OperationsQueueResponse(
        items=[OperationsQueueItem.model_validate(item) for item in items],
        total=total,
        limit=100,
        offset=0,
    )
    
    # 2. SLA Summary
    sla_summary = await SLAService().get_summary(db, SLASummaryQuery())
    
    # 3. Escalations by Status
    escalation_counts = await EscalationRepository().count_by_status(db)
    
    return ComplaintMonitoringResponse(
        operations_queue=ops_queue,
        sla_summary=sla_summary,
        escalation_counts=escalation_counts,
        generated_at=datetime.now(UTC),
    )


# ─── Admin — Audit Logs ───────────────────────────────────────────────────────

@admin_router.get("/audit-logs", response_model=AuditLogListResponse)
async def list_audit_logs(
    actor_employee_id: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    target_type: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _principal=Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN)),
    db: AsyncSession = Depends(get_db_session),
) -> AuditLogListResponse:
    items, total = await EmployeeService().list_audit_logs(
        db,
        actor_employee_id=actor_employee_id,
        action=action,
        target_type=target_type,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )
    return AuditLogListResponse(
        items=[AuditLogEntry(**row) for row in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@admin_router.get("/login-history", response_model=LoginHistoryListResponse)
async def list_login_history(
    employee_id: Optional[str] = Query(None, description="Filter by actor employee_id"),
    success: Optional[bool] = Query(None, description="true=login_success, false=login_failed"),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _principal=Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN)),
    db: AsyncSession = Depends(get_db_session),
) -> LoginHistoryListResponse:
    # Map the success bool to an exact action, or use prefix for both
    action: Optional[str] = None
    action_prefix: Optional[str] = None
    if success is True:
        action = "auth.login_success"
    elif success is False:
        action = "auth.login_failed"
    else:
        action_prefix = "auth.login"

    items, total = await EmployeeService().list_audit_logs(
        db,
        actor_employee_id=employee_id,
        action=action,
        action_prefix=action_prefix,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )
    return LoginHistoryListResponse(
        items=[
            LoginHistoryEntry(
                id=row["id"],
                employee_id=row["actor_employee_id"],
                actor_name=row["actor_name"],
                action=row["action"],
                created_at=row["created_at"],
                details=row["details"],
            )
            for row in items
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


# ─── Me — Audit Logs ──────────────────────────────────────────────────────────

@me_router.get("/audit-logs", response_model=AuditLogListResponse)
async def my_audit_logs(
    actor_employee_id: Optional[str] = Query(None, include_in_schema=False),
    action: Optional[str] = Query(None),
    target_type: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    principal=Depends(get_current_principal),
    db: AsyncSession = Depends(get_db_session),
) -> AuditLogListResponse:
    """Return audit entries for the calling employee only.

    The actor_employee_id query param is accepted but always overridden
    with the caller's own employee_id — prevents information leakage.
    """
    items, total = await EmployeeService().list_audit_logs(
        db,
        actor_employee_id=principal.actor,  # forced to caller's own id
        action=action,
        target_type=target_type,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )
    return AuditLogListResponse(
        items=[AuditLogEntry(**row) for row in items],
        total=total,
        limit=limit,
        offset=offset,
    )

# ─── Admin — Reports ──────────────────────────────────────────────────────────

from fastapi.responses import StreamingResponse
from app.exports.services.csv_service import CSVExportService
from typing import Optional

def _build_timestamp() -> str:
    from datetime import datetime, UTC
    return datetime.now(UTC).strftime("%Y%m%d_%H%M%S")

@admin_router.get("/reports/employee-performance.csv")
async def export_employee_performance_csv(
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    _principal=Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN)),
    db: AsyncSession = Depends(get_db_session),
) -> StreamingResponse:
    from datetime import datetime, timedelta, UTC
    if date_to is None:
        date_to = datetime.now(UTC)
    if date_from is None:
        date_from = date_to - timedelta(days=30)
        
    timestamp = _build_timestamp()
    headers = {
        "Content-Disposition": f'attachment; filename="employee_performance_{timestamp}.csv"',
    }
    return StreamingResponse(
        CSVExportService().stream_employee_performance_csv(db, date_from, date_to),
        media_type="text/csv",
        headers=headers,
    )

@admin_router.get("/reports/department.csv")
async def export_department_report_csv(
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    _principal=Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN)),
    db: AsyncSession = Depends(get_db_session),
) -> StreamingResponse:
    from datetime import datetime, timedelta, UTC
    if date_to is None:
        date_to = datetime.now(UTC)
    if date_from is None:
        date_from = date_to - timedelta(days=30)
        
    timestamp = _build_timestamp()
    headers = {
        "Content-Disposition": f'attachment; filename="department_report_{timestamp}.csv"',
    }
    return StreamingResponse(
        CSVExportService().stream_department_report_csv(db, date_from, date_to),
        media_type="text/csv",
        headers=headers,
    )
