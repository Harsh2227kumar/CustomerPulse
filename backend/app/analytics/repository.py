from collections.abc import Sequence
from datetime import datetime
from typing import Any, Literal

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


async def get_complaint_trends_by_category(
    db: AsyncSession, granularity: Granularity
) -> list[tuple[datetime, str, int]]:
    query = text(
        f"""
        SELECT date_trunc('{granularity}', date_received) AS period, category, count(*) AS count
        FROM complaints
        WHERE date_received IS NOT NULL AND category IS NOT NULL
        GROUP BY period, category
        ORDER BY period ASC, count DESC
        """
    )
    result = await db.execute(query)
    return [(period, category, count) for period, category, count in result.all()]


async def get_complaint_trends_by_channel(
    db: AsyncSession, granularity: Granularity
) -> list[tuple[datetime, str, int]]:
    query = text(
        f"""
        SELECT date_trunc('{granularity}', date_received) AS period, channel, count(*) AS count
        FROM complaints
        WHERE date_received IS NOT NULL AND channel IS NOT NULL
        GROUP BY period, channel
        ORDER BY period ASC, count DESC
        """
    )
    result = await db.execute(query)
    return [(period, channel, count) for period, channel, count in result.all()]


async def get_queue_bottlenecks(
    db: AsyncSession,
) -> dict[str, Any]:
    query = text(
        """
        SELECT
            avg(EXTRACT(EPOCH FROM (processed_at - created_at))) AS avg_intake_to_ai,
            avg(EXTRACT(EPOCH FROM (reviewed_at - processed_at))) AS avg_ai_to_review,
            avg(EXTRACT(EPOCH FROM (reviewed_at - created_at))) AS avg_intake_to_review,
            count(*) FILTER (WHERE processed_at IS NOT NULL) AS processed_count,
            count(*) FILTER (WHERE reviewed_at IS NOT NULL) AS reviewed_count
        FROM complaints
        """
    )
    result = await db.execute(query)
    row = result.fetchone()
    if not row:
        return {
            "avg_intake_to_ai_hours": None,
            "avg_ai_to_review_hours": None,
            "avg_intake_to_review_hours": None,
            "processed_count": 0,
            "reviewed_count": 0,
        }

    def to_hours(seconds):
        return round(float(seconds) / 3600.0, 2) if seconds is not None else None

    return {
        "avg_intake_to_ai_hours": to_hours(row[0]),
        "avg_ai_to_review_hours": to_hours(row[1]),
        "avg_intake_to_review_hours": to_hours(row[2]),
        "processed_count": int(row[3]) if row[3] is not None else 0,
        "reviewed_count": int(row[4]) if row[4] is not None else 0,
    }


async def get_recurring_phrases(
    db: AsyncSession, limit: int = 10
) -> list[tuple[str, int, str | None, str | None]]:
    query = text(
        """
        SELECT issue AS phrase, count(*) AS count, product, category
        FROM complaints
        WHERE issue IS NOT NULL AND ai_status = 'completed'
        GROUP BY issue, product, category
        ORDER BY count DESC
        LIMIT :limit
        """
    )
    result = await db.execute(query, {"limit": limit})
    return [(phrase, count, product, category) for phrase, count, product, category in result.all()]


async def get_product_spikes(
    db: AsyncSession, days_window: int = 7
) -> list[dict[str, Any]]:
    query = text(
        """
        WITH recent_counts AS (
            SELECT product, count(*) AS count
            FROM complaints
            WHERE date_received >= NOW() - (INTERVAL '1 day' * :days)
              AND date_received IS NOT NULL
            GROUP BY product
        ),
        previous_counts AS (
            SELECT product, count(*) AS count
            FROM complaints
            WHERE date_received >= NOW() - (INTERVAL '2 day' * :days)
              AND date_received < NOW() - (INTERVAL '1 day' * :days)
              AND date_received IS NOT NULL
            GROUP BY product
        )
        SELECT
            COALESCE(r.product, p.product) AS product,
            COALESCE(r.count, 0) AS recent_count,
            COALESCE(p.count, 0) AS previous_count
        FROM recent_counts r
        FULL OUTER JOIN previous_counts p ON r.product = p.product
        """
    )
    result = await db.execute(query, {"days": days_window})
    items = []
    for row in result.all():
        product, recent, previous = row[0], int(row[1]), int(row[2])
        if previous == 0:
            growth_rate = float(recent) if recent > 0 else 0.0
        else:
            growth_rate = round((recent - previous) / previous, 4)

        spike_score = round(growth_rate * recent, 2)
        items.append({
            "product": product or "Unknown",
            "recent_count": recent,
            "previous_count": previous,
            "growth_rate": growth_rate,
            "spike_score": spike_score
        })
    items.sort(key=lambda x: x["spike_score"], reverse=True)
    return items


async def get_duplicate_themes(
    db: AsyncSession, limit: int = 10
) -> list[tuple[str, str | None, str | None, str | None, int, datetime]]:
    query = text(
        """
        SELECT dg.id AS group_id, c.product, c.category, c.issue, count(dm.id) AS member_count, dg.created_at
        FROM duplicate_groups dg
        JOIN complaints c ON c.id = dg.canonical_complaint_pk
        LEFT JOIN duplicate_members dm ON dm.group_id = dg.id
        GROUP BY dg.id, c.product, c.category, c.issue, dg.created_at
        ORDER BY member_count DESC, dg.created_at DESC
        LIMIT :limit
        """
    )
    result = await db.execute(query, {"limit": limit})
    return [
        (group_id, product, category, issue, count, created_at)
        for group_id, product, category, issue, count, created_at in result.all()
    ]


async def get_business_impact_kpis(
    db: AsyncSession,
) -> dict[str, Any]:
    query_counts = text(
        """
        SELECT
            count(*) AS total,
            count(*) FILTER (WHERE ai_status = 'completed') AS completed,
            count(*) FILTER (WHERE ai_status = 'completed' AND reviewed_at IS NULL) AS auto_resolved,
            count(*) FILTER (WHERE ai_status = 'completed' AND reviewed_at IS NOT NULL) AS human_reviewed
        FROM complaints
        """
    )
    res_counts = await db.execute(query_counts)
    counts_row = res_counts.fetchone()
    total = int(counts_row[0]) if counts_row[0] is not None else 0
    completed = int(counts_row[1]) if counts_row[1] is not None else 0
    auto_resolved = int(counts_row[2]) if counts_row[2] is not None else 0
    human_reviewed = int(counts_row[3]) if counts_row[3] is not None else 0

    auto_resolution_pct = round(auto_resolved / completed * 100, 2) if completed > 0 else 0.0

    query_latencies = text(
        """
        SELECT
            avg(EXTRACT(EPOCH FROM (processed_at - created_at))) AS avg_ai,
            avg(EXTRACT(EPOCH FROM (reviewed_at - processed_at))) AS avg_review
        FROM complaints
        """
    )
    res_latencies = await db.execute(query_latencies)
    lat_row = res_latencies.fetchone()
    avg_ai = float(lat_row[0]) if lat_row[0] is not None else 0.0
    avg_review = float(lat_row[1]) if lat_row[1] is not None else 0.0

    query_sla = text(
        """
        WITH current_sla AS (
            SELECT
                count(*) AS total,
                count(*) FILTER (WHERE timely_response = false) AS breached
            FROM complaints
            WHERE date_received >= NOW() - INTERVAL '30 day'
              AND date_received IS NOT NULL
        ),
        previous_sla AS (
            SELECT
                count(*) AS total,
                count(*) FILTER (WHERE timely_response = false) AS breached
            FROM complaints
            WHERE date_received >= NOW() - INTERVAL '60 day'
              AND date_received < NOW() - INTERVAL '30 day'
              AND date_received IS NOT NULL
        )
        SELECT
            COALESCE(c.total, 0),
            COALESCE(c.breached, 0),
            COALESCE(p.total, 0),
            COALESCE(p.breached, 0)
        FROM current_sla c, previous_sla p
        """
    )
    res_sla = await db.execute(query_sla)
    sla_row = res_sla.fetchone()
    c_total = int(sla_row[0]) if sla_row else 0
    c_breach = int(sla_row[1]) if sla_row else 0
    p_total = int(sla_row[2]) if sla_row else 0
    p_breach = int(sla_row[3]) if sla_row else 0

    c_breach_rate = round(c_breach / c_total * 100, 2) if c_total > 0 else 0.0
    p_breach_rate = round(p_breach / p_total * 100, 2) if p_total > 0 else 0.0
    breach_reduction = round(p_breach_rate - c_breach_rate, 2)

    query_feedback = text(
        """
        SELECT count(*)
        FROM agent_feedback
        WHERE feedback_action = 'approve'
        """
    )
    res_feedback = await db.execute(query_feedback)
    feedback_row = res_feedback.fetchone()
    approved_drafts = int(feedback_row[0]) if feedback_row else 0

    workload_saved = round((auto_resolved * 0.5) + (approved_drafts * 0.25), 2)

    query_timely = text(
        """
        SELECT
            count(*) FILTER (WHERE timely_response = true) AS timely,
            count(*) AS total
        FROM complaints
        WHERE timely_response IS NOT NULL
        """
    )
    res_timely = await db.execute(query_timely)
    timely_row = res_timely.fetchone()
    t_timely = int(timely_row[0]) if timely_row and timely_row[0] is not None else 0
    t_total = int(timely_row[1]) if timely_row and timely_row[1] is not None else 0
    timely_response_pct = round(t_timely / t_total * 100, 2) if t_total > 0 else 0.0

    return {
        "auto_resolution_pct": auto_resolution_pct,
        "avg_ai_processing_time_sec": avg_ai,
        "avg_human_resolution_time_sec": avg_review,
        "timely_response_pct": timely_response_pct,
        "current_breach_rate_pct": c_breach_rate,
        "previous_breach_rate_pct": p_breach_rate,
        "breach_reduction_rate_pct": breach_reduction,
        "total_processed": completed,
        "total_reviewed": human_reviewed,
        "workload_saved_hours": workload_saved
    }



