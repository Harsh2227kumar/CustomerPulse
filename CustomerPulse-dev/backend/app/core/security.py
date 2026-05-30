from fastapi import HTTPException, status


def require_configured_secret(secret: str | None, name: str) -> str:
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{name} is not configured",
        )
    return secret
