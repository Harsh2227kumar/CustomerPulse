import base64
import hashlib
import hmac
import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, UTC

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.constants import Role
from app.db.session import get_db_session
from app.employees.repository import EmployeeRepository

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class Principal:
    actor: str
    role: Role


def base64url_encode(payload: bytes) -> str:
    return base64.urlsafe_b64encode(payload).rstrip(b"=").decode("utf-8")


def base64url_decode(payload: str) -> bytes:
    padding = "=" * (4 - (len(payload) % 4))
    return base64.urlsafe_b64decode(payload + padding)


def create_jwt_token(payload: dict, secret_key: str) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = base64url_encode(json.dumps(header).encode("utf-8"))
    payload_b64 = base64url_encode(json.dumps(payload).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    signature = hmac.new(secret_key.encode("utf-8"), signing_input, hashlib.sha256).digest()
    signature_b64 = base64url_encode(signature)
    return f"{header_b64}.{payload_b64}.{signature_b64}"


def decode_jwt_token(token: str, secret_key: str) -> dict | None:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        header_b64, payload_b64, signature_b64 = parts
        signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
        expected_sig = hmac.new(secret_key.encode("utf-8"), signing_input, hashlib.sha256).digest()
        expected_sig_b64 = base64url_encode(expected_sig)
        
        if not hmac.compare_digest(signature_b64.encode("utf-8"), expected_sig_b64.encode("utf-8")):
            return None
            
        payload = json.loads(base64url_decode(payload_b64).decode("utf-8"))
        return payload
    except Exception:
        return None


def require_configured_secret(secret: str | None, name: str) -> str:
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{name} is not configured",
        )
    return secret


async def get_current_principal(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    settings: Settings = Depends(get_settings),
    db: AsyncSession = Depends(get_db_session),
) -> Principal:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer authentication is required.",
        )
    
    token = credentials.credentials

    # 1. Try decoding as a JWT token
    payload = decode_jwt_token(token, settings.jwt_secret_key)
    if payload is not None:
        exp = payload.get("exp")
        if exp is not None:
            if datetime.now(UTC).timestamp() > exp:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has expired.",
                )
        
        employee_id = payload.get("sub")
        if employee_id:
            repo = EmployeeRepository()
            employee = await repo.get_by_employee_id(db, employee_id)
            if employee is not None:
                if employee.status != "active":
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Account is not active.",
                    )
                return Principal(actor=employee.employee_id, role=Role(employee.role))

    # 2. Fallback to legacy auth_principals for backwards compatibility with tests
    raw = settings.auth_principals.get(token)
    if raw is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid bearer credentials.",
        )
    return Principal(actor=raw["actor"], role=Role(raw["role"]))


def require_roles(*roles: Role) -> Callable[[Principal], Principal]:
    allowed = set(roles)

    def dependency(principal: Principal = Depends(get_current_principal)) -> Principal:
        if principal.role == Role.SUPER_ADMIN or principal.role in allowed:
            return principal
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient role for this action.",
        )

    return dependency
