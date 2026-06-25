from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.repository import (
    get_complaint_trends,
    get_complaint_trends_by_category,
    get_complaint_trends_by_channel,
    get_high_urgency,
    get_human_review_trends,
    get_product_summary,
    get_queue_bottlenecks,
    get_recurring_phrases,
    get_product_spikes,
    get_duplicate_themes,
    get_business_impact_kpis,
)
from app.analytics.schemas import (
    HighUrgencyItem,
    HighUrgencyResponse,
    ProductSummaryResponse,
    ProductSummaryRow,
    TrendPoint,
    TrendResponse,
    TrendByCategoryPoint,
    TrendByCategoryResponse,
    TrendByChannelPoint,
    TrendByChannelResponse,
    BottleneckMetricsResponse,
    RecurringIssuePhrase,
    RecurringPhrasesResponse,
    ProductSpikeItem,
    ProductSpikesResponse,
    DuplicateThemeItem,
    DuplicateThemesResponse,
    BusinessImpactKPIsResponse,
)
from app.db.session import get_db_session

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

Granularity = Literal["day", "week", "month"]


@router.get("/complaint-trends", response_model=TrendResponse)
async def complaint_trends(
    granularity: Granularity = Query(default="day"),
    db: AsyncSession = Depends(get_db_session),
) -> TrendResponse:
    items = await get_complaint_trends(db, granularity)
    return TrendResponse(
        items=[TrendPoint(period=period.isoformat(), count=count) for period, count in items],
        granularity=granularity,
    )


@router.get("/product-summary", response_model=ProductSummaryResponse)
async def product_summary(
    db: AsyncSession = Depends(get_db_session),
) -> ProductSummaryResponse:
    items = await get_product_summary(db)
    return ProductSummaryResponse(
        items=[
            ProductSummaryRow(
                product=product,
                category=category,
                count=count,
                avg_urgency=float(avg_urgency) if avg_urgency is not None else None,
            )
            for product, category, count, avg_urgency in items
        ]
    )


@router.get("/human-review-trends", response_model=TrendResponse)
async def human_review_trends(
    granularity: Granularity = Query(default="week"),
    db: AsyncSession = Depends(get_db_session),
) -> TrendResponse:
    items = await get_human_review_trends(db, granularity)
    return TrendResponse(
        items=[TrendPoint(period=period.isoformat(), count=count) for period, count in items],
        granularity=granularity,
    )


@router.get("/high-urgency", response_model=HighUrgencyResponse)
async def high_urgency(
    threshold: int = Query(default=70, ge=0, le=100),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db_session),
) -> HighUrgencyResponse:
    items, count = await get_high_urgency(db, threshold, limit, offset)
    return HighUrgencyResponse(
        items=[
            HighUrgencyItem(
                complaint_id=item.id,
                narrative=item.narrative,
                product=item.product,
                channel=item.channel,
                urgency_score=item.urgency_score if item.urgency_score is not None else threshold,
                sentiment=item.sentiment,
                created_at=item.created_at,
            )
            for item in items
        ],
        count=count,
        limit=limit,
        offset=offset,
    )


@router.get("/trends/category", response_model=TrendByCategoryResponse)
async def trend_by_category(
    granularity: Granularity = Query(default="day"),
    db: AsyncSession = Depends(get_db_session),
) -> TrendByCategoryResponse:
    items = await get_complaint_trends_by_category(db, granularity)
    return TrendByCategoryResponse(
        items=[
            TrendByCategoryPoint(
                period=period.isoformat(),
                category=category,
                count=count
            )
            for period, category, count in items
        ],
        granularity=granularity,
    )


@router.get("/trends/channel", response_model=TrendByChannelResponse)
async def trend_by_channel(
    granularity: Granularity = Query(default="day"),
    db: AsyncSession = Depends(get_db_session),
) -> TrendByChannelResponse:
    items = await get_complaint_trends_by_channel(db, granularity)
    return TrendByChannelResponse(
        items=[
            TrendByChannelPoint(
                period=period.isoformat(),
                channel=channel,
                count=count
            )
            for period, channel, count in items
        ],
        granularity=granularity,
    )


@router.get("/bottlenecks", response_model=BottleneckMetricsResponse)
async def bottlenecks(
    db: AsyncSession = Depends(get_db_session),
) -> BottleneckMetricsResponse:
    metrics = await get_queue_bottlenecks(db)
    return BottleneckMetricsResponse(**metrics)


@router.get("/root-causes/phrases", response_model=RecurringPhrasesResponse)
async def root_causes_phrases(
    limit: int = Query(default=10, ge=1, le=50),
    db: AsyncSession = Depends(get_db_session),
) -> RecurringPhrasesResponse:
    items = await get_recurring_phrases(db, limit)
    return RecurringPhrasesResponse(
        items=[
            RecurringIssuePhrase(
                phrase=phrase,
                count=count,
                product=product,
                category=category
            )
            for phrase, count, product, category in items
        ]
    )


@router.get("/root-causes/spikes", response_model=ProductSpikesResponse)
async def root_causes_spikes(
    days_window: int = Query(default=7, ge=1, le=30),
    db: AsyncSession = Depends(get_db_session),
) -> ProductSpikesResponse:
    items = await get_product_spikes(db, days_window)
    return ProductSpikesResponse(
        items=[ProductSpikeItem(**item) for item in items]
    )


@router.get("/root-causes/themes", response_model=DuplicateThemesResponse)
async def root_causes_themes(
    limit: int = Query(default=10, ge=1, le=50),
    db: AsyncSession = Depends(get_db_session),
) -> DuplicateThemesResponse:
    items = await get_duplicate_themes(db, limit)
    return DuplicateThemesResponse(
        items=[
            DuplicateThemeItem(
                group_id=group_id,
                product=product,
                category=category,
                issue=issue,
                member_count=member_count,
                created_at=created_at
            )
            for group_id, product, category, issue, member_count, created_at in items
        ]
    )


@router.get("/business-impact", response_model=BusinessImpactKPIsResponse)
async def business_impact(
    db: AsyncSession = Depends(get_db_session),
) -> BusinessImpactKPIsResponse:
    kpis = await get_business_impact_kpis(db)
    return BusinessImpactKPIsResponse(**kpis)

