from sqlalchemy.ext.asyncio import AsyncSession

from app.feedback.models import AgentFeedback
from app.feedback.repository import FeedbackRepository
from app.feedback.schemas import AgentFeedbackUpsertRequest, FeedbackListQuery, FeedbackListResponse, FeedbackRead


class ComplaintNotFoundError(LookupError):
    pass


class FeedbackNotFoundError(LookupError):
    pass


class FeedbackService:
    def __init__(self, repository: FeedbackRepository | None = None) -> None:
        self.repository = repository or FeedbackRepository()

    async def upsert_feedback(
        self,
        db: AsyncSession,
        complaint_id: str,
        payload: AgentFeedbackUpsertRequest,
    ) -> tuple[FeedbackRead, bool]:
        complaint = await self.repository.get_complaint_by_source_id(db, complaint_id)
        if complaint is None:
            raise ComplaintNotFoundError(complaint_id)

        created = not await self.repository.feedback_exists(db, complaint.id)
        feedback = await self.repository.upsert_feedback(db, complaint.id, payload)
        return self._to_feedback_read(feedback, complaint.source_complaint_id or complaint.id), created

    async def get_feedback(
        self,
        db: AsyncSession,
        complaint_id: str,
    ) -> FeedbackRead:
        record = await self.repository.get_feedback_with_complaint_id(db, complaint_id)
        if record is None:
            raise FeedbackNotFoundError(complaint_id)
        feedback, resolved_complaint_id = record
        return self._to_feedback_read(feedback, resolved_complaint_id)

    async def list_feedback(
        self,
        db: AsyncSession,
        filters: FeedbackListQuery,
    ) -> FeedbackListResponse:
        rows, count = await self.repository.list_feedback(db, filters)
        items = [self._to_feedback_read(feedback, complaint_id) for feedback, complaint_id in rows]
        return FeedbackListResponse(
            items=items,
            limit=filters.limit,
            offset=filters.offset,
            count=count,
        )

    async def export_feedback(
        self,
        db: AsyncSession,
    ) -> list[FeedbackRead]:
        rows = await self.repository.export_feedback(db)
        return [self._to_feedback_read(feedback, complaint_id) for feedback, complaint_id in rows]

    def _to_feedback_read(self, feedback: AgentFeedback, complaint_id: str) -> FeedbackRead:
        return FeedbackRead(
            complaint_id=complaint_id,
            agent_id=feedback.agent_id,
            feedback_action=feedback.feedback_action,
            final_response=feedback.final_response,
            action_used=feedback.action_used,
            human_review_outcome=feedback.human_review_outcome,
            similar_cases_useful=feedback.similar_cases_useful,
            notes=feedback.notes,
            revision_count=feedback.revision_count,
            submitted_at=feedback.submitted_at,
            updated_at=feedback.updated_at,
        )
