from datetime import datetime
from typing import Any, Optional, Literal
from pydantic import BaseModel, ConfigDict, Field


# ─── Department ───────────────────────────────────────────────────────────────

class DepartmentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    code: str = Field(..., min_length=1, max_length=50)


class DepartmentUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    code: Optional[str] = Field(None, min_length=1, max_length=50)


class DepartmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    code: str
    created_at: datetime


class DepartmentWithCount(BaseModel):
    """DepartmentRead extended with a live employee_count."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    code: str
    created_at: datetime
    employee_count: int = 0


class DepartmentListResponse(BaseModel):
    items: list[DepartmentWithCount]
    total: int
    limit: int
    offset: int


# ─── Employee ─────────────────────────────────────────────────────────────────

class EmployeeCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=8, max_length=100)
    role: Literal["agent", "manager", "admin", "super_admin"]
    department_id: Optional[str] = None
    reports_to: Optional[str] = None


class EmployeeUpdate(BaseModel):
    """Updatable fields via PATCH /api/admin/employees/{id}.
    Status and password changes are handled by dedicated endpoints.
    """
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[str] = Field(None, min_length=3, max_length=255)
    role: Optional[Literal["agent", "manager", "admin", "super_admin"]] = None
    department_id: Optional[str] = None
    reports_to: Optional[str] = None


class EmployeeAssignRequest(BaseModel):
    """Body for POST /api/admin/employees/{id}/assign.
    Both fields are optional — only provided fields are updated.
    """
    department_id: Optional[str] = None
    reports_to: Optional[str] = None


class EmployeeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    employee_id: str
    name: str
    email: str
    role: str
    department_id: Optional[str] = None
    reports_to: Optional[str] = None
    status: str
    must_change_password: bool
    created_at: datetime
    created_by: Optional[str] = None
    updated_at: datetime


class EmployeeListResponse(BaseModel):
    items: list[EmployeeRead]
    total: int
    limit: int
    offset: int


# ─── Action request bodies ────────────────────────────────────────────────────

class SuspendRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=500)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=100)


class ResetPasswordResponse(BaseModel):
    temporary_password: str


# ─── AuditLog ─────────────────────────────────────────────────────────────────

class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    actor_employee_id: Optional[str] = None
    action: str
    target_type: Optional[str] = None
    target_id: Optional[str] = None
    details: Optional[dict[str, Any]] = None
    created_at: datetime


class AuditLogEntry(BaseModel):
    """Enriched audit log entry with resolved actor_name."""
    id: str
    actor_employee_id: Optional[str] = None
    actor_name: Optional[str] = None
    action: str
    target_type: Optional[str] = None
    target_id: Optional[str] = None
    details: Optional[dict[str, Any]] = None
    created_at: datetime


class AuditLogListResponse(BaseModel):
    items: list[AuditLogEntry]
    total: int
    limit: int
    offset: int


class LoginHistoryEntry(BaseModel):
    """Login-specific audit entry."""
    id: str
    employee_id: Optional[str] = None
    actor_name: Optional[str] = None
    action: str
    created_at: datetime
    details: Optional[dict[str, Any]] = None


class LoginHistoryListResponse(BaseModel):
    items: list[LoginHistoryEntry]
    total: int
    limit: int
    offset: int


# ─── Auth ─────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    password: str


class LoginResponse(BaseModel):
    access_token: str
    role: str
    employee_id: str
    must_change_password: bool


# ─── Admin Dashboard ──────────────────────────────────────────────────────────

class EmployeeStatusCounts(BaseModel):
    total: int
    active: int
    suspended: int
    inactive: int


class AdminDashboardResponse(BaseModel):
    """Aggregated dashboard snapshot for admin views.

    ``recently_active_employees`` is the count of employees with an
    ``auth.login_success`` audit entry in the last 30 minutes.  This is
    *not* a real-time online-presence indicator — no session/heartbeat
    tracking exists in the system.
    """
    employee_counts: EmployeeStatusCounts
    role_counts: dict[str, int]
    department_count: int
    recently_active_employees: int
    complaints_today: int
    open_complaints: int
    escalated_complaints: int
    sla_breaches_today: int
    generated_at: datetime
