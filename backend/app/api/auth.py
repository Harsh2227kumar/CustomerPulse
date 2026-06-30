"""
Auth API: username/password login -> Bearer token lookup.

Users are configured via AUTH_USERS_JSON in .env:
  [{"username": "admin", "password": "admin123", "role": "admin", "api_key": "..."}]

The same /api/auth/login endpoint also accepts employee email/password credentials
and returns a JWT for the employee/admin tables.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.security import create_jwt_token, decode_jwt_token
from app.db.session import get_db_session
from app.employees.repository import EmployeeRepository
from app.employees.service import AccountSuspendedError, EmployeeService, InvalidCredentialsError

router = APIRouter(prefix="/api/auth", tags=["auth"])

bearer_scheme = HTTPBearer(auto_error=False)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class LoginRequest(BaseModel):
    username: str | None = None
    email: str | None = None
    password: str


class UserProfile(BaseModel):
    username: str
    actor: str
    role: str
    display_name: str


class LoginResponse(BaseModel):
    api_key: str | None = None
    user: UserProfile | None = None
    access_token: str | None = None
    role: str | None = None
    employee_id: str | None = None
    must_change_password: bool | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_users(settings: Settings) -> list[dict[str, Any]]:
    """Parse AUTH_USERS_JSON from settings. Returns [] if unset."""
    raw = getattr(settings, "auth_users_json", None) or "[]"
    try:
        users = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(users, list):
        return []
    return users


def _find_user_by_key(settings: Settings, api_key: str) -> dict[str, Any] | None:
    """Lookup a user record by its api_key."""
    for user in _load_users(settings):
        if user.get("api_key") == api_key:
            return user
    return None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/login", response_model=LoginResponse)
async def login(
    body: LoginRequest,
    settings: Annotated[Settings, Depends(get_settings)],
    db: AsyncSession = Depends(get_db_session),
) -> LoginResponse:
    """Validate legacy or employee credentials and return a bearer credential."""
    if body.username:
        for user in _load_users(settings):
            if user.get("username") == body.username and user.get("password") == body.password:
                return LoginResponse(
                    api_key=user["api_key"],
                    user=UserProfile(
                        username=user["username"],
                        actor=user.get("actor", user["username"]),
                        role=user["role"],
                        display_name=user.get("display_name", user["username"].title()),
                    ),
                )

    employee_email = body.email or body.username
    if employee_email:
        try:
            employee = await EmployeeService().authenticate(db, employee_email, body.password)
        except InvalidCredentialsError:
            employee = None
        except AccountSuspendedError as exc:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(exc),
            ) from exc
        if employee is not None:
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

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid username/email or password.",
    )


@router.get("/me", response_model=UserProfile)
async def me(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    settings: Annotated[Settings, Depends(get_settings)],
    db: AsyncSession = Depends(get_db_session),
) -> UserProfile:
    """Return the profile of the currently authenticated user."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer authentication required.",
        )

    payload = decode_jwt_token(credentials.credentials, settings.jwt_secret_key)
    if payload is not None:
        employee_id = payload.get("sub")
        if employee_id:
            employee = await EmployeeRepository().get_by_employee_id(db, employee_id)
            if employee is not None and employee.status == "active":
                return UserProfile(
                    username=employee.email,
                    actor=employee.employee_id,
                    role=employee.role,
                    display_name=employee.name,
                )

    # Try the legacy user table first (richer profile)
    user = _find_user_by_key(settings, credentials.credentials)
    if user:
        return UserProfile(
            username=user["username"],
            actor=user.get("actor", user["username"]),
            role=user["role"],
            display_name=user.get("display_name", user["username"].title()),
        )

    # Fall back to the raw principals dict (api-key-only entries)
    raw = settings.auth_principals.get(credentials.credentials)
    if raw:
        return UserProfile(
            username=raw["actor"],
            actor=raw["actor"],
            role=raw["role"],
            display_name=raw["actor"].replace("-", " ").title(),
        )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired credentials.",
    )


