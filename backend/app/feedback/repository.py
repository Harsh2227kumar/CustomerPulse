from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.feedback.models import AgentFeedback
from app.feedback.schemas import AgentFeedbackUpsertRequest, FeedbackListQuery
from app.models.complaint import Complaint


class FeedbackRepository:
    async def get_complaint_by_source_id(
        self,
        db: AsyncSession,
        source_complaint_id: str,
    ) -> Complaint | None:
        stmt = select(Complaint).where(Complaint.source_complaint_id == source_complaint_id)
        return (await db.execute(stmt)).scalar_one_or_none()

    async def feedback_exists(
        self,
        db: AsyncSession,
        complaint_pk: str,
    ) -> bool:
        stmt = select(AgentFeedback.id).where(AgentFeedback.complaint_pk == complaint_pk)
        return (await db.execute(stmt)).scalar_one_or_none() is not None

    async def upsert_feedback(
        self,
        db: AsyncSession,
        complaint_pk: str,
        payload: AgentFeedbackUpsertRequest,
    ) -> AgentFeedback:
        values = {
            "complaint_pk": complaint_pk,
            "agent_id": payload.agent_id,
            "feedback_action": payload.feedback_action.value,
            "final_response": payload.final_response,
            "action_used": payload.action_used,
            "human_review_outcome": payload.human_review_outcome.value,
            "similar_cases_useful": payload.similar_cases_useful,
            "notes": payload.notes,
            "revision_count": 0,
        }
        stmt = insert(AgentFeedback).values(**values)
        stmt = stmt.on_conflict_do_update(
            index_elements=[AgentFeedback.complaint_pk],
            set_={
                "agent_id": stmt.excluded.agent_id,
                "feedback_action": stmt.excluded.feedback_action,
                "final_response": stmt.excluded.final_response,
                "action_used": stmt.excluded.action_used,
                "human_review_outcome": stmt.excluded.human_review_outcome,
                "similar_cases_useful": stmt.excluded.similar_cases_useful,
                "notes": stmt.excluded.notes,
                "revision_count": AgentFeedback.revision_count + 1,
                "updated_at": func.now(),
            },
        ).returning(AgentFeedback)
        feedback = (await db.execute(stmt)).scalar_one()
        await db.commit()
        return feedback

    async def get_feedback_with_complaint_id(
        self,
        db: AsyncSession,
        source_complaint_id: str,
    ) -> tuple[AgentFeedback, str] | None:
        stmt = (
            select(AgentFeedback, Complaint.source_complaint_id, Complaint.id)
            .join(Complaint, Complaint.id == AgentFeedback.complaint_pk)
            .where(Complaint.source_complaint_id == source_complaint_id)
        )
        row = (await db.execute(stmt)).one_or_none()
        if row is None:
            return None
        feedback, complaint_id, complaint_pk = row
        return feedback, complaint_id or complaint_pk

    async def list_feedback(
        self,
        db: AsyncSession,
        filters: FeedbackListQuery,
    ) -> tuple[Sequence[tuple[AgentFeedback, str]], int]:
        stmt = (
            select(AgentFeedback, Complaint.source_complaint_id, Complaint.id)
            .join(Complaint, Complaint.id == AgentFeedback.complaint_pk)
        )
        count_stmt = (
            select(func.count())
            .select_from(AgentFeedback)
            .join(Complaint, Complaint.id == AgentFeedback.complaint_pk)
        )

        if filters.agent_id:
            stmt = stmt.where(AgentFeedback.agent_id == filters.agent_id)
            count_stmt = count_stmt.where(AgentFeedback.agent_id == filters.agent_id)
        if filters.feedback_action:
            stmt = stmt.where(AgentFeedback.feedback_action == filters.feedback_action.value)
            count_stmt = count_stmt.where(AgentFeedback.feedback_action == filters.feedback_action.value)

        stmt = stmt.order_by(AgentFeedback.submitted_at.desc()).limit(filters.limit).offset(filters.offset)
        rows = (await db.execute(stmt)).all()
        count = (await db.execute(count_stmt)).scalar_one()
        items = [(feedback, complaint_id or complaint_pk) for feedback, complaint_id, complaint_pk in rows]
        return items, count

    async def export_feedback(
        self,
        db: AsyncSession,
    ) -> Sequence[tuple[AgentFeedback, str]]:
        stmt = (
            select(AgentFeedback, Complaint.source_complaint_id, Complaint.id)
            .join(Complaint, Complaint.id == AgentFeedback.complaint_pk)
            .order_by(AgentFeedback.submitted_at.asc())
        )
        rows = (await db.execute(stmt)).all()
        return [(feedback, complaint_id or complaint_pk) for feedback, complaint_id, complaint_pk in rows]
