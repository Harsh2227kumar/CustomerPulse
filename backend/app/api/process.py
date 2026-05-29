from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.constants import ProcessingTrigger, Role
from app.core.security import Principal, require_roles
from app.db.session import get_db_session
from app.schemas.ai_response import ProcessedComplaintResponse
from app.schemas.complaint import ComplaintProcessRequest
from app.services.processing_service import ComplaintNotFoundError, ProcessingService

router = APIRouter(prefix="/api", tags=["processing"])


@router.post("/process", response_model=ProcessedComplaintResponse)
async def process_complaint(
    complaint: ComplaintProcessRequest,
    db: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
    principal: Principal = Depends(require_roles(Role.AGENT, Role.MANAGER, Role.ADMIN)),
) -> ProcessedComplaintResponse:
    service = ProcessingService(settings)
    return await service.process_complaint(
        db,
        complaint,
        trigger=ProcessingTrigger.API_REQUEST,
        initiated_by=principal.actor,
    )


@router.post("/process/{complaint_id}", response_model=ProcessedComplaintResponse)
async def process_imported_complaint(
    complaint_id: str,
    db: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
    principal: Principal = Depends(require_roles(Role.AGENT, Role.MANAGER, Role.ADMIN)),
) -> ProcessedComplaintResponse:
    service = ProcessingService(settings)
    try:
        return await service.process_imported_complaint(
            db,
            complaint_id,
            trigger=ProcessingTrigger.IMPORTED_REQUEST,
            initiated_by=principal.actor,
        )
    except ComplaintNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Complaint not found.") from exc
