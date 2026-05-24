from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
async def health_check() -> dict[str, str | bool]:
    settings = get_settings()
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "s3_import_configured": settings.s3_import_configured,
    }
