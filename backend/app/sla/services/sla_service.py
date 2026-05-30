from datetime import datetime
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.sla.repositories.sla_repository import SLARepository
from app.sla.schemas.sla_schemas import (
    SLABreachRiskItem,
    SLABreachRiskQuery,
    SLABreachRiskResponse,
    SLAGroupedItem,
    SLAGroupedQuery,
    SLAGroupedResponse,
    SLAGroupSortBy,
    SLASummaryQuery,
    SLASummaryResponse,
    SLATrendGranularity,
    SLATrendItem,
    SLATrendQuery,
    SLATrendResponse,
)


logger = logging.getLogger(__name__)

HIGH_URGENCY_THRESHOLD = 70


class SLAService:
    def __init__(self, repository: SLARepository | None = None) -> None:
        self.repository = repository or SLARepository()

    async def get_summary(
        self,
        db: AsyncSession,
        filters: SLASummaryQuery,
    ) -> SLASummaryResponse:
        self._validate_date_range(filters.date_from, filters.date_to)
        summary = await self.repository.get_summary(
            db,
            date_from=filters.date_from,
            date_to=filters.date_to,
            product=filters.product,
            channel=filters.channel,
            high_urgency_threshold=HIGH_URGENCY_THRESHOLD,
        )
        total_complaints = int(summary["total_complaints"] or 0)
        timely_count = int(summary["timely_count"] or 0)
        untimely_count = int(summary["untimely_count"] or 0)
        high_urgency_untimely_count = int(summary["high_urgency_untimely_count"] or 0)

        if high_urgency_untimely_count > 100:
            logger.warning(
                "High urgency untimely complaints exceeded warning threshold: %s",
                high_urgency_untimely_count,
            )

        return SLASummaryResponse(
            total_complaints=total_complaints,
            timely_count=timely_count,
            untimely_count=untimely_count,
            timely_rate_pct=self._percentage(timely_count, total_complaints),
            avg_urgency_score=self._round_nullable(summary["avg_urgency_score"]),
            high_urgency_untimely_count=high_urgency_untimely_count,
            period_from=filters.date_from,
            period_to=filters.date_to,
        )

    async def get_by_product(
        self,
        db: AsyncSession,
        filters: SLAGroupedQuery,
    ) -> SLAGroupedResponse:
        return await self._get_grouped_response(db, filters, group_by="product")

    async def get_by_channel(
        self,
        db: AsyncSession,
        filters: SLAGroupedQuery,
    ) -> SLAGroupedResponse:
        return await self._get_grouped_response(db, filters, group_by="channel")

    async def get_breach_risk(
        self,
        db: AsyncSession,
        filters: SLABreachRiskQuery,
    ) -> SLABreachRiskResponse:
        self._validate_limit(filters.limit, maximum=200)
        items, total = await self.repository.get_breach_risk(
            db,
            urgency_threshold=filters.urgency_threshold,
            churn_risk=filters.churn_risk,
            limit=filters.limit,
            offset=filters.offset,
        )
        return SLABreachRiskResponse(
            items=[SLABreachRiskItem.model_validate(item) for item in items],
            total=total,
            limit=filters.limit,
            offset=filters.offset,
        )

    async def get_trend(
        self,
        db: AsyncSession,
        filters: SLATrendQuery,
    ) -> SLATrendResponse:
        self._validate_date_range(filters.date_from, filters.date_to)
        granularity = self._resolve_granularity(filters.granularity)
        rows = await self.repository.get_trend(
            db,
            granularity=granularity,
            date_from=filters.date_from,
            date_to=filters.date_to,
            product=filters.product,
        )
        return SLATrendResponse(
            granularity=filters.granularity,
            items=[
                SLATrendItem(
                    period=self._format_period(item["period"], filters.granularity),
                    total=int(item["total"] or 0),
                    timely=int(item["timely"] or 0),
                    untimely=int(item["untimely"] or 0),
                    timely_rate_pct=self._percentage(
                        int(item["timely"] or 0),
                        int(item["total"] or 0),
                    ),
                )
                for item in rows
            ],
        )

    async def _get_grouped_response(
        self,
        db: AsyncSession,
        filters: SLAGroupedQuery,
        *,
        group_by: str,
    ) -> SLAGroupedResponse:
        self._validate_date_range(filters.date_from, filters.date_to)
        self._validate_limit(filters.limit, maximum=100)
        self._validate_sort_by(filters.sort_by)
        rows, count = await self.repository.get_grouped_summary(
            db,
            group_by=group_by,
            date_from=filters.date_from,
            date_to=filters.date_to,
            limit=filters.limit,
            sort_by=filters.sort_by,
        )
        return SLAGroupedResponse(
            items=[
                SLAGroupedItem(
                    product=row.get("product") if group_by == "product" else None,
                    channel=row.get("channel") if group_by == "channel" else None,
                    total=int(row["total"] or 0),
                    timely=int(row["timely"] or 0),
                    untimely=int(row["untimely"] or 0),
                    timely_rate_pct=self._percentage(
                        int(row["timely"] or 0),
                        int(row["total"] or 0),
                    ),
                    avg_urgency_score=self._round_nullable(row["avg_urgency_score"]),
                )
                for row in rows
            ],
            count=count,
        )

    def _validate_date_range(
        self,
        date_from: datetime | None,
        date_to: datetime | None,
    ) -> None:
        if date_from and date_to and date_from > date_to:
            raise ValueError("date_from must be less than or equal to date_to")

    def _validate_limit(self, value: int, *, maximum: int) -> None:
        if value < 1 or value > maximum:
            raise ValueError(f"limit must be between 1 and {maximum}")

    def _validate_sort_by(self, sort_by: SLAGroupSortBy) -> None:
        if sort_by not in {
            SLAGroupSortBy.TIMELY_RATE,
            SLAGroupSortBy.TOTAL,
            SLAGroupSortBy.UNTIMELY_COUNT,
        }:
            raise ValueError("Unsupported sort_by value")

    def _resolve_granularity(self, granularity: SLATrendGranularity | str) -> str:
        if granularity == SLATrendGranularity.WEEKLY:
            return "week"
        if granularity == SLATrendGranularity.MONTHLY:
            return "month"
        raise ValueError("Unsupported granularity")

    def _format_period(self, period: datetime, granularity: SLATrendGranularity) -> str:
        if granularity == SLATrendGranularity.WEEKLY:
            return period.date().isoformat()
        return period.strftime("%Y-%m")

    def _percentage(self, numerator: int, denominator: int) -> float:
        if denominator == 0:
            return 0.0
        return round((numerator / denominator) * 100, 2)

    def _round_nullable(self, value: object) -> float | None:
        if value is None:
            return None
        return round(float(value), 2)
