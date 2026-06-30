from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.repository import (
    get_complaint_trends,
    get_complaint_volume_insights,
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
    ComplaintVolumeGroupItem,
    ComplaintVolumeHeatmapItem,
    ComplaintVolumeInsightsResponse,
    ComplaintVolumeMixItem,
    ComplaintVolumeSampleItem,
    ComplaintVolumeSummary,
    ComplaintVolumeTimelineItem,
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



VolumeGroupBy = Literal["product", "channel", "category", "sentiment", "churn_risk", "ai_status"]


@router.get("/complaint-volume-insights", response_model=ComplaintVolumeInsightsResponse)
async def complaint_volume_insights(
    granularity: Granularity = Query(default="week"),
    group_by: VolumeGroupBy = Query(default="product"),
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = Query(default=12, ge=3, le=50),
    db: AsyncSession = Depends(get_db_session),
) -> ComplaintVolumeInsightsResponse:
    data = await get_complaint_volume_insights(
        db,
        granularity=granularity,
        group_by=group_by,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
    )
    timeline_rows = data["timeline"]
    total_count = sum(row["total"] for row in timeline_rows)
    peak = max(timeline_rows, key=lambda row: row["total"], default=None)
    avg_urgency_values = [float(row["avg_urgency"]) for row in timeline_rows if row["avg_urgency"] is not None]
    avg_urgency = sum(avg_urgency_values) / len(avg_urgency_values) if avg_urgency_values else None

    return ComplaintVolumeInsightsResponse(
        granularity=granularity,
        group_by=group_by,
        summary=ComplaintVolumeSummary(
            total_count=total_count,
            avg_per_period=(total_count / len(timeline_rows)) if timeline_rows else 0,
            peak_period=peak["period"].isoformat() if peak else None,
            peak_count=peak["total"] if peak else 0,
            high_urgency_count=sum(row["high_urgency"] for row in timeline_rows),
            human_review_count=sum(row["human_review"] for row in timeline_rows),
            negative_count=sum(row["negative"] for row in timeline_rows),
            avg_urgency=avg_urgency,
        ),
        timeline=[
            ComplaintVolumeTimelineItem(
                period=row["period"].isoformat(),
                total=row["total"],
                high_urgency=row["high_urgency"],
                human_review=row["human_review"],
                negative=row["negative"],
                timely=row["timely"],
                untimely=row["untimely"],
                avg_urgency=float(row["avg_urgency"]) if row["avg_urgency"] is not None else None,
            )
            for row in timeline_rows
        ],
        groups=[
            ComplaintVolumeGroupItem(
                group=row["group_value"],
                count=row["count"],
                avg_urgency=float(row["avg_urgency"]) if row["avg_urgency"] is not None else None,
                high_urgency=row["high_urgency"],
                negative=row["negative"],
                human_review=row["human_review"],
            )
            for row in data["groups"]
        ],
        heatmap=[
            ComplaintVolumeHeatmapItem(
                product=row["product"],
                channel=row["channel"],
                count=row["count"],
                avg_urgency=float(row["avg_urgency"]) if row["avg_urgency"] is not None else None,
            )
            for row in data["heatmap"]
        ],
        sentiment_mix=[ComplaintVolumeMixItem(label=row["label"], count=row["count"]) for row in data["sentiment_mix"]],
        status_mix=[ComplaintVolumeMixItem(label=row["label"], count=row["count"]) for row in data["status_mix"]],
        samples=[
            ComplaintVolumeSampleItem(
                complaint_id=row["complaint_id"],
                product=row["product"],
                channel=row["channel"],
                category=row["category"],
                sentiment=row["sentiment"],
                ai_status=row["ai_status"],
                urgency_score=row["urgency_score"],
                date_received=row["date_received"],
                narrative=row["narrative"],
            )
            for row in data["samples"]
        ],
    )


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

