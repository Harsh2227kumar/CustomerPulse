from datetime import datetime

from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import ChurnRisk, ProcessingStatus
from app.models.complaint import Complaint
from app.sla.schemas.sla_schemas import SLAGroupSortBy


class SLARepository:
    def _completed_conditions(
        self,
        *,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        product: str | None = None,
        channel: str | None = None,
        require_date_received: bool = False,
    ) -> list[object]:
        conditions: list[object] = [Complaint.ai_status == ProcessingStatus.COMPLETED.value]
        if date_from is not None:
            conditions.append(Complaint.date_received >= date_from)
        if date_to is not None:
            conditions.append(Complaint.date_received <= date_to)
        if product:
            conditions.append(Complaint.product == product)
        if channel:
            conditions.append(Complaint.channel == channel)
        if require_date_received:
            conditions.append(Complaint.date_received.is_not(None))
        return conditions

    async def get_summary(
        self,
        db: AsyncSession,
        *,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        product: str | None = None,
        channel: str | None = None,
        high_urgency_threshold: int = 70,
    ) -> dict[str, object]:
        conditions = self._completed_conditions(
            date_from=date_from,
            date_to=date_to,
            product=product,
            channel=channel,
        )
        stmt = select(
            func.count(Complaint.id).label("total_complaints"),
            func.count(Complaint.id)
            .filter(Complaint.timely_response.is_(True))
            .label("timely_count"),
            func.count(Complaint.id)
            .filter(Complaint.timely_response.is_(False))
            .label("untimely_count"),
            func.avg(Complaint.urgency_score).label("avg_urgency_score"),
            func.count(Complaint.id)
            .filter(
                and_(
                    Complaint.urgency_score >= high_urgency_threshold,
                    Complaint.timely_response.is_(False),
                )
            )
            .label("high_urgency_untimely_count"),
        ).where(*conditions)
        row = (await db.execute(stmt)).mappings().one()
        return dict(row)

    async def get_grouped_summary(
        self,
        db: AsyncSession,
        *,
        group_by: str,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        limit: int = 20,
        sort_by: SLAGroupSortBy = SLAGroupSortBy.TIMELY_RATE,
    ) -> tuple[list[dict[str, object]], int]:
        group_column = Complaint.product if group_by == "product" else Complaint.channel
        conditions = self._completed_conditions(date_from=date_from, date_to=date_to)
        timely_count = func.count(Complaint.id).filter(Complaint.timely_response.is_(True))
        untimely_count = func.count(Complaint.id).filter(Complaint.timely_response.is_(False))
        total_count = func.count(Complaint.id)
        timely_rate = (timely_count * 100.0 / func.nullif(total_count, 0)).label("timely_rate_pct")
        stmt = (
            select(
                group_column.label(group_by),
                total_count.label("total"),
                timely_count.label("timely"),
                untimely_count.label("untimely"),
                timely_rate,
                func.avg(Complaint.urgency_score).label("avg_urgency_score"),
            )
            .where(*conditions)
            .group_by(group_column)
        )

        if sort_by == SLAGroupSortBy.TOTAL:
            stmt = stmt.order_by(desc(total_count), group_column.asc())
        elif sort_by == SLAGroupSortBy.UNTIMELY_COUNT:
            stmt = stmt.order_by(desc(untimely_count), group_column.asc())
        else:
            stmt = stmt.order_by(desc(timely_rate), desc(total_count), group_column.asc())

        count_stmt = select(func.count()).select_from(
            select(group_column).where(*conditions).group_by(group_column).subquery()
        )
        rows = (await db.execute(stmt.limit(limit))).mappings().all()
        total_groups = (await db.execute(count_stmt)).scalar_one()
        return [dict(row) for row in rows], total_groups

    async def get_breach_risk(
        self,
        db: AsyncSession,
        *,
        urgency_threshold: int = 70,
        churn_risk: ChurnRisk | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict[str, object]], int]:
        conditions = self._completed_conditions()
        conditions.append(Complaint.urgency_score >= urgency_threshold)
        conditions.append(
            or_(Complaint.timely_response.is_(None), Complaint.timely_response.is_(False))
        )
        if churn_risk:
            conditions.append(Complaint.churn_risk == churn_risk.value)

        complaint_id = func.coalesce(Complaint.source_complaint_id, Complaint.id).label("complaint_id")
        stmt = (
            select(
                complaint_id,
                Complaint.source_complaint_id,
                Complaint.channel,
                Complaint.product,
                Complaint.timely_response,
                Complaint.date_received,
                Complaint.urgency_score,
                Complaint.churn_risk,
                Complaint.processed_at,
                Complaint.created_at,
            )
            .where(*conditions)
            .order_by(desc(Complaint.urgency_score), desc(Complaint.created_at))
            .limit(limit)
            .offset(offset)
        )
        count_stmt = select(func.count()).select_from(Complaint).where(*conditions)
        rows = (await db.execute(stmt)).mappings().all()
        total = (await db.execute(count_stmt)).scalar_one()
        return [dict(row) for row in rows], total

    async def get_trend(
        self,
        db: AsyncSession,
        *,
        granularity: str,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        product: str | None = None,
    ) -> list[dict[str, object]]:
        conditions = self._completed_conditions(
            date_from=date_from,
            date_to=date_to,
            product=product,
            require_date_received=True,
        )
        period = func.date_trunc(granularity, Complaint.date_received).label("period")
        timely_count = func.count(Complaint.id).filter(Complaint.timely_response.is_(True))
        untimely_count = func.count(Complaint.id).filter(Complaint.timely_response.is_(False))
        total_count = func.count(Complaint.id)
        stmt = (
            select(
                period,
                total_count.label("total"),
                timely_count.label("timely"),
                untimely_count.label("untimely"),
            )
            .where(*conditions)
            .group_by(period)
            .order_by(period.asc())
        )
        rows = (await db.execute(stmt)).mappings().all()
        return [dict(row) for row in rows]

    async def is_breach_risk_for_complaint(
        self,
        db: AsyncSession,
        complaint_pk: str,
        *,
        urgency_threshold: int = 70,
    ) -> bool:
        conditions = self._completed_conditions()
        conditions.append(Complaint.id == complaint_pk)
        conditions.append(Complaint.urgency_score >= urgency_threshold)
        conditions.append(
            or_(Complaint.timely_response.is_(None), Complaint.timely_response.is_(False))
        )
        count_stmt = select(func.count()).select_from(Complaint).where(*conditions)
        total = (await db.execute(count_stmt)).scalar_one()
        return total > 0
