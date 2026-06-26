from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.communications.schemas import (
    CommunicationEntryCreate,
    CommunicationEntryRead,
    TimelineResponse,
)
from app.communications.service import (
    CommunicationComplaintNotFoundError,
    CommunicationService,
)
from app.communications.workspace import workspace_router
from app.core.constants import Role
from app.core.security import require_roles
from app.db.session import get_db_session

router = APIRouter(prefix="/api/complaints", tags=["communications"])
router.include_router(workspace_router)


@router.get("/{complaint_id}/timeline", response_model=TimelineResponse)
async def get_timeline(
    complaint_id: str,
    _principal=Depends(require_roles(Role.AGENT, Role.MANAGER, Role.ADMIN)),
    db: AsyncSession = Depends(get_db_session),
) -> TimelineResponse:
    try:
        return await CommunicationService().get_timeline(db, complaint_id)
    except CommunicationComplaintNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Complaint not found") from exc


@router.post("/{complaint_id}/timeline", response_model=CommunicationEntryRead)
async def add_timeline_note(
    complaint_id: str,
    payload: CommunicationEntryCreate,
    principal=Depends(require_roles(Role.AGENT, Role.MANAGER, Role.ADMIN)),
    db: AsyncSession = Depends(get_db_session),
) -> CommunicationEntryRead:
    try:
        return await CommunicationService().add_note(
            db, complaint_id, payload, actor=principal.actor
        )
    except CommunicationComplaintNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Complaint not found") from exc
