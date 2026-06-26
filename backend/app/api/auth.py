"""
Auth API: username/password login → Bearer token lookup.

Users are configured via AUTH_USERS_JSON in .env:
  [{"username": "admin", "password": "admin123", "role": "admin", "api_key": "..."}]

The api_key must also appear in AUTH_PRINCIPALS_JSON so that the existing
Bearer-key middleware continues to work unchanged.
"""

from __future__ import annotations

import json
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from app.core.config import Settings, get_settings

router = APIRouter(prefix="/api/auth", tags=["auth"])

bearer_scheme = HTTPBearer(auto_error=False)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class LoginRequest(BaseModel):
    username: str
    password: str


class UserProfile(BaseModel):
    username: str
    actor: str
    role: str
    display_name: str


class LoginResponse(BaseModel):
    api_key: str
    user: UserProfile


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
) -> LoginResponse:
    """Validate username + password; return the user's API key and profile."""
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
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid username or password.",
    )


@router.get("/me", response_model=UserProfile)
async def me(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> UserProfile:
    """Return the profile of the currently authenticated user."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer authentication required.",
        )

    # Try the user table first (richer profile)
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
