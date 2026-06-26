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

VOLUME_GROUP_COLUMNS = {
    "product": "product",
    "channel": "channel",
    "category": "category",
    "sentiment": "sentiment",
    "churn_risk": "churn_risk",
    "ai_status": "ai_status",
}


async def get_complaint_volume_insights(
    db: AsyncSession,
    granularity: Granularity,
    group_by: str,
    date_from: datetime | None,
    date_to: datetime | None,
    limit: int,
) -> dict:
    group_column = VOLUME_GROUP_COLUMNS[group_by]
    filters = ["date_received IS NOT NULL"]
    params: dict[str, object] = {"limit": limit}
    if date_from is not None:
        filters.append("date_received >= :date_from")
        params["date_from"] = date_from
    if date_to is not None:
        filters.append("date_received <= :date_to")
        params["date_to"] = date_to
    where_clause = " AND ".join(filters)

    timeline_result = await db.execute(
        text(
            f"""
            SELECT
                date_trunc('{granularity}', date_received) AS period,
                count(*) AS total,
                count(*) FILTER (WHERE urgency_score >= 70) AS high_urgency,
                count(*) FILTER (WHERE ai_status = 'human_review') AS human_review,
                count(*) FILTER (WHERE sentiment = 'Negative') AS negative,
                count(*) FILTER (WHERE timely_response IS TRUE) AS timely,
                count(*) FILTER (WHERE timely_response IS FALSE) AS untimely,
                avg(urgency_score) AS avg_urgency
            FROM complaints
            WHERE {where_clause}
            GROUP BY period
            ORDER BY period ASC
            """
        ),
        params,
    )
    timeline = timeline_result.mappings().all()

    groups_result = await db.execute(
        text(
            f"""
            SELECT
                coalesce({group_column}, 'Unknown') AS group_value,
                count(*) AS count,
                avg(urgency_score) AS avg_urgency,
                count(*) FILTER (WHERE urgency_score >= 70) AS high_urgency,
                count(*) FILTER (WHERE sentiment = 'Negative') AS negative,
                count(*) FILTER (WHERE ai_status = 'human_review') AS human_review
            FROM complaints
            WHERE {where_clause}
            GROUP BY group_value
            ORDER BY count DESC
            LIMIT :limit
            """
        ),
        params,
    )
    groups = groups_result.mappings().all()

    heatmap_result = await db.execute(
        text(
            f"""
            SELECT
                coalesce(product, 'Unknown') AS product,
                coalesce(channel, 'Unknown') AS channel,
                count(*) AS count,
                avg(urgency_score) AS avg_urgency
            FROM complaints
            WHERE {where_clause}
            GROUP BY product, channel
            ORDER BY count DESC
            LIMIT 80
            """
        ),
        params,
    )
    heatmap = heatmap_result.mappings().all()

    sentiment_result = await db.execute(
        text(
            f"""
            SELECT coalesce(sentiment, 'Unknown') AS label, count(*) AS count
            FROM complaints
            WHERE {where_clause}
            GROUP BY label
            ORDER BY count DESC
            """
        ),
        params,
    )
    sentiment_mix = sentiment_result.mappings().all()

    status_result = await db.execute(
        text(
            f"""
            SELECT coalesce(ai_status, 'Unknown') AS label, count(*) AS count
            FROM complaints
            WHERE {where_clause}
            GROUP BY label
            ORDER BY count DESC
            """
        ),
        params,
    )
    status_mix = status_result.mappings().all()

    samples_result = await db.execute(
        text(
            f"""
            SELECT
                id AS complaint_id,
                product,
                channel,
                category,
                sentiment,
                ai_status,
                urgency_score,
                date_received,
                narrative
            FROM complaints
            WHERE {where_clause}
            ORDER BY urgency_score DESC NULLS LAST, date_received DESC NULLS LAST
            LIMIT 8
            """
        ),
        params,
    )
    samples = samples_result.mappings().all()

    return {
        "timeline": timeline,
        "groups": groups,
        "heatmap": heatmap,
        "sentiment_mix": sentiment_mix,
        "status_mix": status_mix,
        "samples": samples,
    }

