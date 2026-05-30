from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import EMBEDDING_DIMENSIONS, ProcessingStatus
from app.models.complaint import Complaint
from app.schemas.ai_response import SimilarCaseEvidence


class SimilarComplaintService:
    async def retrieve(
        self,
        db: AsyncSession,
        active_complaint: Complaint,
        query_embedding: list[float],
        *,
        threshold: float,
        limit: int,
    ) -> list[SimilarCaseEvidence]:
        self._validate_query(query_embedding, threshold, limit)
        distance = Complaint.embedding.cosine_distance(query_embedding)
        similarity = (1 - distance).label("similarity_score")
        rows = (
            await db.execute(
                select(Complaint, similarity)
                .where(
                    Complaint.id != active_complaint.id,
                    Complaint.embedding.is_not(None),
                    Complaint.ai_status == ProcessingStatus.COMPLETED.value,
                    distance <= 1 - threshold,
                )
                .order_by(distance.asc(), Complaint.id.asc())
                .limit(limit)
            )
        ).all()
        return [
            SimilarCaseEvidence(
                complaint_id=complaint.source_complaint_id or complaint.id,
                similarity_score=round(max(0.0, min(1.0, float(score))), 4),
                category=complaint.category,
                next_action=complaint.next_action,
                approved_response=complaint.approved_response,
                ai_status=complaint.ai_status,
            )
            for complaint, score in rows
        ]

    def _validate_query(
        self, query_embedding: list[float], threshold: float, limit: int
    ) -> None:
        if len(query_embedding) != EMBEDDING_DIMENSIONS:
            raise ValueError(
                f"Query embedding must contain {EMBEDDING_DIMENSIONS} dimensions."
            )
        if not 0 <= threshold <= 1:
            raise ValueError("Similarity threshold must be between 0 and 1.")
        if limit < 1:
            raise ValueError("Similar-case result limit must be positive.")
