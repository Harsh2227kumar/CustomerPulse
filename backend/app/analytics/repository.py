from collections.abc import Sequence
from datetime import datetime
from typing import Literal

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.complaint import Complaint


Granularity = Literal["day", "week", "month"]


async def get_complaint_trends(
    db: AsyncSession, granularity: Granularity
) -> list[tuple[datetime, int]]:
    query = text(
        f"""
        SELECT date_trunc('{granularity}', date_received) AS period, count(*) AS count
        FROM complaints
        WHERE date_received IS NOT NULL
        GROUP BY period
        ORDER BY period ASC
        """
    )
    result = await db.execute(query)
    return [(period, count) for period, count in result.all()]


async def get_product_summary(
    db: AsyncSession,
) -> list[tuple[str | None, str | None, int, float | None]]:
    query = text(
        """
        SELECT product, category, count(*) AS count, avg(urgency_score) AS avg_urgency
        FROM complaints
        WHERE ai_status = 'completed'
        GROUP BY product, category
        ORDER BY count DESC
        """
    )
    result = await db.execute(query)
    return [
        (product, category, count, avg_urgency)
        for product, category, count, avg_urgency in result.all()
    ]


async def get_human_review_trends(
    db: AsyncSession, granularity: Granularity
) -> list[tuple[datetime, int]]:
    query = text(
        f"""
        SELECT date_trunc('{granularity}', date_received) AS period, count(*) AS count
        FROM complaints
        WHERE ai_status = 'completed' AND date_received IS NOT NULL
        GROUP BY period
        ORDER BY period ASC
        """
    )
    result = await db.execute(query)
    return [(period, count) for period, count in result.all()]


async def get_high_urgency(
    db: AsyncSession, threshold: int, limit: int, offset: int
) -> tuple[Sequence[Complaint], int]:
    items_result = await db.execute(
        select(Complaint)
        .where(Complaint.urgency_score >= threshold)
        .order_by(Complaint.urgency_score.desc())
        .limit(limit)
        .offset(offset)
    )
    count_result = await db.execute(
        select(func.count()).select_from(Complaint).where(Complaint.urgency_score >= threshold)
    )
    return items_result.scalars().all(), count_result.scalar_one()

