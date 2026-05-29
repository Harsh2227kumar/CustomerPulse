from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.constants import ProcessingTrigger, Role
from app.core.security import Principal, require_roles
from app.db.session import get_db_session
from app.schemas.ai_response import ProcessedComplaintResponse
from app.schemas.complaint import ApproveReviewRequest, ComplaintDetail, ResolveReviewRequest
from app.services.processing_service import ComplaintNotFoundError, ProcessingService
from app.services.review_service import ReviewService, ReviewStateError


router = APIRouter(prefix="/api/complaints", tags=["review"])


@router.post("/{complaint_id}/review/approve", response_model=ComplaintDetail)
async def approve_review(
    complaint_id: str,
    request: ApproveReviewRequest,
    db: AsyncSession = Depends(get_db_session),
    principal: Principal = Depends(require_roles(Role.MANAGER, Role.ADMIN)),
) -> ComplaintDetail:
    try:
        detail = await ReviewService().approve(db, complaint_id, request, principal)
    except ReviewStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if detail is None:
        raise HTTPException(status_code=404, detail="Complaint not found.")
    return detail


@router.post("/{complaint_id}/review/resolve", response_model=ComplaintDetail)
async def resolve_review(
    complaint_id: str,
    request: ResolveReviewRequest,
    db: AsyncSession = Depends(get_db_session),
    principal: Principal = Depends(require_roles(Role.MANAGER, Role.ADMIN)),
) -> ComplaintDetail:
    try:
        detail = await ReviewService().resolve(db, complaint_id, request, principal)
    except ReviewStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if detail is None:
        raise HTTPException(status_code=404, detail="Complaint not found.")
    return detail


@router.post("/{complaint_id}/review/rerun", response_model=ProcessedComplaintResponse)
async def rerun_review(
    complaint_id: str,
    db: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
    principal: Principal = Depends(require_roles(Role.AGENT, Role.MANAGER, Role.ADMIN)),
) -> ProcessedComplaintResponse:
    try:
        return await ProcessingService(settings).process_imported_complaint(
            db,
            complaint_id,
            trigger=ProcessingTrigger.REVIEW_RERUN,
            initiated_by=principal.actor,
        )
    except ComplaintNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Complaint not found.") from exc
