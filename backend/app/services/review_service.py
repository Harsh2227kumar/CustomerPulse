from datetime import UTC, datetime

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import ProcessingStatus
from app.core.security import Principal
from app.models.complaint import Complaint
from app.schemas.complaint import ApproveReviewRequest, ComplaintDetail, ResolveReviewRequest
from app.services.complaint_service import ComplaintService


class ReviewStateError(ValueError):
    pass


class ReviewService:
    async def approve(
        self,
        db: AsyncSession,
        complaint_id: str,
        request: ApproveReviewRequest,
        principal: Principal,
    ) -> ComplaintDetail | None:
        complaint = await self._find(db, complaint_id)
        if complaint is None:
            return None
        self._require_review(complaint)
        approved_response = (request.approved_response or complaint.draft_response or "").strip()
        if not approved_response:
            raise ReviewStateError("An approved response is required.")
        complaint.approved_response = approved_response
        complaint.review_resolution = "approved"
        complaint.review_notes = request.notes
        complaint.reviewer = principal.actor
        complaint.reviewed_at = datetime.now(UTC)
        complaint.ai_status = ProcessingStatus.COMPLETED.value
        await db.commit()
        return await ComplaintService().get_detail(db, complaint_id)

    async def resolve(
        self,
        db: AsyncSession,
        complaint_id: str,
        request: ResolveReviewRequest,
        principal: Principal,
    ) -> ComplaintDetail | None:
        complaint = await self._find(db, complaint_id)
        if complaint is None:
            return None
        self._require_review(complaint)
        complaint.review_resolution = request.resolution
        complaint.review_notes = request.notes
        complaint.reviewer = principal.actor
        complaint.reviewed_at = datetime.now(UTC)
        complaint.ai_status = ProcessingStatus.COMPLETED.value
        await db.commit()
        return await ComplaintService().get_detail(db, complaint_id)

    async def _find(self, db: AsyncSession, complaint_id: str) -> Complaint | None:
        return (
            await db.execute(
                select(Complaint).where(
                    or_(Complaint.source_complaint_id == complaint_id, Complaint.id == complaint_id)
                )
            )
        ).scalar_one_or_none()

    def _require_review(self, complaint: Complaint) -> None:
        if complaint.ai_status != ProcessingStatus.HUMAN_REVIEW.value:
            raise ReviewStateError("Complaint is not awaiting human review.")
