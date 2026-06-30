from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.constants import Role
from app.core.security import Principal, require_roles
from app.db.session import get_db_session
from app.ingestion.email_intake import EmailIntakeService
from app.schemas.ingestion import EmailSyncResponse

router = APIRouter(prefix="/api/ingestion/email", tags=["ingestion"])


@router.post(
    "/sync",
    response_model=EmailSyncResponse,
    status_code=status.HTTP_200_OK,
)
async def sync_emails(
    db: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
    principal: Principal = Depends(require_roles(Role.MANAGER, Role.ADMIN)),
) -> EmailSyncResponse:
    """Manually trigger email synchronization and ingestion."""
    if not settings.email_intake_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email intake is not enabled."
        )

    service = EmailIntakeService(settings)
    try:
        stats = await service.sync_emails(db)
        if stats["status"] == "failed":
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=stats["error_message"] or "Email sync failed."
            )
        return EmailSyncResponse(
            status=stats["status"],
            scanned_emails=stats["scanned_emails"],
            imported_emails=stats["imported_emails"],
            skipped_emails=stats["skipped_emails"],
            failed_emails=stats["failed_emails"],
            error_message=stats["error_message"]
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred during email sync: {exc}"
        )
