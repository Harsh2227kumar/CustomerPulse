from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import ChurnRisk, ProcessingStatus, ReviewReason, Role, Sentiment
from app.core.security import Principal, require_roles
from app.db.session import get_db_session
from app.schemas.complaint import ComplaintAssignRequest, ComplaintDetail, ComplaintFilters, ComplaintListResponse
from app.services.complaint_service import ComplaintService

router = APIRouter(prefix="/api", tags=["complaints"])


@router.get("/complaints", response_model=ComplaintListResponse)
async def list_complaints(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    sentiment: Sentiment | None = None,
    channel: str | None = None,
    product: str | None = None,
    churn_risk: ChurnRisk | None = None,
    urgency_min: int | None = Query(default=None, ge=0, le=100),
    urgency_max: int | None = Query(default=None, ge=0, le=100),
    date_received_min: datetime | None = None,
    date_received_max: datetime | None = None,
    timely_response: bool | None = None,
    ai_status: ProcessingStatus | None = None,
    human_review_reason: ReviewReason | None = None,
    search: str | None = Query(default=None, max_length=256),
    sort_by: Literal[
        "created_at",
        "date_received",
        "processed_at",
        "urgency_score",
        "sentiment",
        "churn_risk",
        "ai_confidence",
        "ai_status",
        "relevance",
    ] = "created_at",
    sort_direction: Literal["asc", "desc"] = "desc",
    db: AsyncSession = Depends(get_db_session),
) -> ComplaintListResponse:
    try:
        filters = ComplaintFilters(
            limit=limit,
            offset=offset,
            sentiment=sentiment,
            channel=channel,
            product=product,
            churn_risk=churn_risk,
            urgency_min=urgency_min,
            urgency_max=urgency_max,
            date_received_min=date_received_min,
            date_received_max=date_received_max,
            timely_response=timely_response,
            ai_status=ai_status,
            human_review_reason=human_review_reason,
            search=search,
            sort_by=sort_by,
            sort_direction=sort_direction,
        )
    except ValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail="Invalid complaint filter or sorting combination.",
        ) from exc
    return await ComplaintService().list_complaints(db, filters)


@router.get("/complaints/{complaint_id}", response_model=ComplaintDetail)
async def get_complaint_detail(
    complaint_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> ComplaintDetail:
    detail = await ComplaintService().get_detail(db, complaint_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Complaint not found.")
    return detail


@router.post("/complaints/{complaint_id}/assign", response_model=ComplaintDetail)
async def assign_complaint(
    complaint_id: str,
    request: ComplaintAssignRequest,
    db: AsyncSession = Depends(get_db_session),
    principal: Principal = Depends(require_roles(Role.MANAGER, Role.ADMIN)),
) -> ComplaintDetail:
    detail = await ComplaintService().assign_agent(db, complaint_id, request.agent_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Complaint not found.")
    return detail
