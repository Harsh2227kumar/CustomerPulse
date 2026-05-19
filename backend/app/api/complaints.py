from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import ChurnRisk, Sentiment
from app.db.session import get_db_session
from app.schemas.complaint import ComplaintFilters, ComplaintListResponse
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
    search: str | None = None,
    sort_by: str = "created_at",
    sort_direction: str = Query(default="desc", pattern="^(asc|desc)$"),
    db: AsyncSession = Depends(get_db_session),
) -> ComplaintListResponse:
    filters = ComplaintFilters(
        limit=limit,
        offset=offset,
        sentiment=sentiment,
        channel=channel,
        product=product,
        churn_risk=churn_risk,
        urgency_min=urgency_min,
        urgency_max=urgency_max,
        search=search,
        sort_by=sort_by,
        sort_direction=sort_direction,
    )
    return await ComplaintService().list_complaints(db, filters)
