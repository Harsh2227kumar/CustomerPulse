from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import ChurnRisk
from app.db.session import get_db_session
from app.sla.schemas.sla_schemas import (
    SLABreachRiskQuery,
    SLABreachRiskResponse,
    SLAGroupedQuery,
    SLAGroupedResponse,
    SLAGroupSortBy,
    SLASummaryQuery,
    SLASummaryResponse,
    SLATrendGranularity,
    SLATrendQuery,
    SLATrendResponse,
)
from app.sla.services.sla_service import SLAService

router = APIRouter(prefix="/api/sla", tags=["SLA"])


@router.get("/summary", response_model=SLASummaryResponse)
async def get_sla_summary(
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    product: str | None = Query(default=None, max_length=255),
    channel: str | None = Query(default=None, max_length=64),
    db: AsyncSession = Depends(get_db_session),
) -> SLASummaryResponse:
    filters = SLASummaryQuery(
        date_from=date_from,
        date_to=date_to,
        product=product,
        channel=channel,
    )
    return await SLAService().get_summary(db, filters)


@router.get("/by-product", response_model=SLAGroupedResponse)
async def get_sla_by_product(
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    sort_by: SLAGroupSortBy = Query(default=SLAGroupSortBy.TIMELY_RATE),
    db: AsyncSession = Depends(get_db_session),
) -> SLAGroupedResponse:
    filters = SLAGroupedQuery(
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        sort_by=sort_by,
    )
    return await SLAService().get_by_product(db, filters)


@router.get("/by-channel", response_model=SLAGroupedResponse)
async def get_sla_by_channel(
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    sort_by: SLAGroupSortBy = Query(default=SLAGroupSortBy.TIMELY_RATE),
    db: AsyncSession = Depends(get_db_session),
) -> SLAGroupedResponse:
    filters = SLAGroupedQuery(
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        sort_by=sort_by,
    )
    return await SLAService().get_by_channel(db, filters)


@router.get("/breach-risk", response_model=SLABreachRiskResponse)
async def get_sla_breach_risk(
    urgency_threshold: int = Query(default=70, ge=0, le=100),
    churn_risk: ChurnRisk | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db_session),
) -> SLABreachRiskResponse:
    filters = SLABreachRiskQuery(
        urgency_threshold=urgency_threshold,
        churn_risk=churn_risk,
        limit=limit,
        offset=offset,
    )
    return await SLAService().get_breach_risk(db, filters)


@router.get("/trend", response_model=SLATrendResponse)
async def get_sla_trend(
    granularity: SLATrendGranularity = Query(default=SLATrendGranularity.MONTHLY),
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    product: str | None = Query(default=None, max_length=255),
    db: AsyncSession = Depends(get_db_session),
) -> SLATrendResponse:
    filters = SLATrendQuery(
        granularity=granularity,
        date_from=date_from,
        date_to=date_to,
        product=product,
    )
    return await SLAService().get_trend(db, filters)
