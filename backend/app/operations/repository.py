from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import HIGH_URGENCY_REVIEW_THRESHOLD, ProcessingStatus
from app.escalations.models import Escalation
from app.models.complaint import Complaint


class OperationsRepository:
    async def get_queue(
        self,
        db: AsyncSession,
        *,
        limit: int,
        offset: int,
    ) -> tuple[list[dict], int]:
        # Build the open-escalation subquery used for the LEFT JOIN
        open_esc = (
            select(
                Escalation.complaint_pk,
                Escalation.id.label("escalation_id"),
            )
            .where(Escalation.status == "open")
            .subquery("open_esc")
        )

        complaint_id_col = func.coalesce(
            Complaint.source_complaint_id, Complaint.id
        ).label("complaint_id")

        has_open = (open_esc.c.escalation_id.is_not(None)).label("has_open_escalation")

        stmt = (
            select(
                complaint_id_col,
                Complaint.source_complaint_id,
                Complaint.channel,
                Complaint.product,
                Complaint.urgency_score,
                Complaint.churn_risk,
                Complaint.ai_status,
                Complaint.human_review_reason,
                has_open,
                open_esc.c.escalation_id,
                Complaint.created_at,
                Complaint.processed_at,
            )
            .outerjoin(open_esc, open_esc.c.complaint_pk == Complaint.id)
            .where(
                or_(
                    Complaint.ai_status == ProcessingStatus.HUMAN_REVIEW.value,
                    Complaint.urgency_score >= HIGH_URGENCY_REVIEW_THRESHOLD,
                    open_esc.c.escalation_id.is_not(None),
                )
            )
            .order_by(
                Complaint.urgency_score.desc().nullslast(),
                Complaint.created_at.asc(),
            )
            .limit(limit)
            .offset(offset)
        )

        # Matching count query
        count_stmt = (
            select(func.count())
            .select_from(Complaint)
            .outerjoin(open_esc, open_esc.c.complaint_pk == Complaint.id)
            .where(
                or_(
                    Complaint.ai_status == ProcessingStatus.HUMAN_REVIEW.value,
                    Complaint.urgency_score >= HIGH_URGENCY_REVIEW_THRESHOLD,
                    open_esc.c.escalation_id.is_not(None),
                )
            )
        )

        rows = (await db.execute(stmt)).mappings().all()
        total = (await db.execute(count_stmt)).scalar_one()
        return [dict(row) for row in rows], total
