from sqlalchemy import Select, asc, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.complaint import Complaint
from app.models.processing import ComplaintProcessingRun
from app.schemas.ai_response import ConfidenceScores, SimilarCaseEvidence
from app.schemas.complaint import (
    ComplaintDetail,
    ComplaintFilters,
    ComplaintListItem,
    ComplaintListResponse,
    ProcessingRunItem,
)


SORTABLE_COLUMNS = {
    "created_at": Complaint.created_at,
    "date_received": Complaint.date_received,
    "processed_at": Complaint.processed_at,
    "urgency_score": Complaint.urgency_score,
    "sentiment": Complaint.sentiment,
    "churn_risk": Complaint.churn_risk,
    "ai_confidence": Complaint.ai_confidence,
    "ai_status": Complaint.ai_status,
}


class ComplaintService:
    async def list_complaints(
        self,
        db: AsyncSession,
        filters: ComplaintFilters,
    ) -> ComplaintListResponse:
        stmt = self._apply_filters(select(Complaint), filters)
        count_stmt = self._apply_filters(select(func.count()).select_from(Complaint), filters)
        count = (await db.execute(count_stmt)).scalar_one()
        stmt = (
            stmt.order_by(*self._order_expressions(filters))
            .limit(filters.limit)
            .offset(filters.offset)
        )
        rows = (await db.execute(stmt)).scalars().all()
        return ComplaintListResponse(
            items=[self._to_list_item(row) for row in rows],
            limit=filters.limit,
            offset=filters.offset,
            count=count,
        )

    async def get_detail(self, db: AsyncSession, complaint_id: str) -> ComplaintDetail | None:
        complaint = (
            await db.execute(
                select(Complaint).where(
                    or_(Complaint.source_complaint_id == complaint_id, Complaint.id == complaint_id)
                )
            )
        ).scalar_one_or_none()
        if complaint is None:
            return None
        runs = (
            await db.execute(
                select(ComplaintProcessingRun)
                .where(ComplaintProcessingRun.complaint_id == complaint.id)
                .order_by(ComplaintProcessingRun.created_at.desc())
            )
        ).scalars().all()
        return ComplaintDetail(
            **self._to_list_item(complaint).model_dump(),
            draft_response=complaint.draft_response,
            next_action=complaint.next_action,
            ai_confidence=complaint.ai_confidence,
            ai_reasoning=complaint.ai_reasoning,
            reviewed_at=complaint.reviewed_at,
            reviewer=complaint.reviewer,
            review_resolution=complaint.review_resolution,
            approved_response=complaint.approved_response,
            review_notes=complaint.review_notes,
            embedding_model=complaint.embedding_model,
            embedded_at=complaint.embedded_at,
            processing_runs=[
                ProcessingRunItem(
                    id=run.id,
                    attempt_number=run.attempt_number,
                    status_outcome=run.status_outcome,
                    trigger_reason=run.trigger_reason,
                    initiated_by=run.initiated_by,
                    error_category=run.error_category,
                    created_at=run.created_at,
                    finished_at=run.finished_at,
                )
                for run in runs
            ],
        )

    def _apply_filters(self, stmt: Select, filters: ComplaintFilters) -> Select:
        if filters.sentiment:
            stmt = stmt.where(Complaint.sentiment == filters.sentiment.value)
        if filters.channel:
            stmt = stmt.where(Complaint.channel == filters.channel)
        if filters.product:
            stmt = stmt.where(Complaint.product == filters.product)
        if filters.churn_risk:
            stmt = stmt.where(Complaint.churn_risk == filters.churn_risk.value)
        if filters.urgency_min is not None:
            stmt = stmt.where(Complaint.urgency_score >= filters.urgency_min)
        if filters.urgency_max is not None:
            stmt = stmt.where(Complaint.urgency_score <= filters.urgency_max)
        if filters.date_received_min is not None:
            stmt = stmt.where(Complaint.date_received >= filters.date_received_min)
        if filters.date_received_max is not None:
            stmt = stmt.where(Complaint.date_received <= filters.date_received_max)
        if filters.timely_response is not None:
            stmt = stmt.where(Complaint.timely_response == filters.timely_response)
        if filters.ai_status:
            stmt = stmt.where(Complaint.ai_status == filters.ai_status.value)
        if filters.human_review_reason:
            stmt = stmt.where(Complaint.human_review_reason == filters.human_review_reason.value)
        if filters.search and filters.search.strip():
            stmt = stmt.where(Complaint.search_vector.op("@@")(self._search_query(filters.search)))
        return stmt

    def _order_expressions(self, filters: ComplaintFilters) -> tuple:
        if filters.sort_by == "relevance" and filters.search and filters.search.strip():
            rank = func.ts_rank(Complaint.search_vector, self._search_query(filters.search))
            primary = asc(rank) if filters.sort_direction == "asc" else desc(rank)
            return (primary, desc(Complaint.created_at), asc(Complaint.id))
        sort_column = SORTABLE_COLUMNS.get(filters.sort_by, Complaint.created_at)
        primary = asc(sort_column) if filters.sort_direction == "asc" else desc(sort_column)
        return (primary.nulls_last(), asc(Complaint.id))

    def _search_query(self, search: str):
        return func.websearch_to_tsquery("english", search.strip())

    def _to_list_item(self, complaint: Complaint) -> ComplaintListItem:
        confidence_scores = None
        if complaint.confidence_scores:
            confidence_scores = ConfidenceScores.model_validate(complaint.confidence_scores)
        evidence = [
            SimilarCaseEvidence.model_validate(item)
            for item in (complaint.similar_case_evidence or [])
        ]
        return ComplaintListItem(
            complaint_id=complaint.source_complaint_id or complaint.id,
            narrative=complaint.narrative,
            channel=complaint.channel,
            product=complaint.product,
            issue=complaint.issue,
            date_received=complaint.date_received,
            timely_response=self._format_timely_response(complaint.timely_response),
            sentiment=complaint.sentiment,
            category=complaint.category,
            urgency_score=complaint.urgency_score,
            churn_risk=complaint.churn_risk,
            confidence_scores=confidence_scores,
            processed_at=complaint.processed_at,
            ai_status=complaint.ai_status,
            human_review_reason=complaint.human_review_reason,
            human_review_created_at=complaint.human_review_created_at,
            similar_cases=evidence,
        )

    def _format_timely_response(self, value: bool | None) -> str | None:
        if value is None:
            return None
        return "Yes" if value else "No"
