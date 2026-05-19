from sqlalchemy import Select, asc, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.complaint import Complaint
from app.schemas.ai_response import ConfidenceScores
from app.schemas.complaint import ComplaintFilters, ComplaintListItem, ComplaintListResponse


SORTABLE_COLUMNS = {
    "created_at": Complaint.created_at,
    "processed_at": Complaint.processed_at,
    "urgency_score": Complaint.urgency_score,
    "sentiment": Complaint.sentiment,
    "churn_risk": Complaint.churn_risk,
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

        sort_column = SORTABLE_COLUMNS.get(filters.sort_by, Complaint.created_at)
        order_by = asc(sort_column) if filters.sort_direction == "asc" else desc(sort_column)
        stmt = stmt.order_by(order_by).limit(filters.limit).offset(filters.offset)
        rows = (await db.execute(stmt)).scalars().all()
        return ComplaintListResponse(
            items=[self._to_list_item(row) for row in rows],
            limit=filters.limit,
            offset=filters.offset,
            count=count,
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
        if filters.search:
            pattern = f"%{filters.search}%"
            stmt = stmt.where(
                or_(
                    Complaint.narrative.ilike(pattern),
                    Complaint.category.ilike(pattern),
                    Complaint.company.ilike(pattern),
                    Complaint.issue.ilike(pattern),
                )
            )
        return stmt

    def _to_list_item(self, complaint: Complaint) -> ComplaintListItem:
        confidence_scores = None
        if complaint.confidence_scores:
            confidence_scores = ConfidenceScores.model_validate(complaint.confidence_scores)
        return ComplaintListItem(
            complaint_id=complaint.source_complaint_id or complaint.id,
            narrative=complaint.narrative,
            channel=complaint.channel,
            product=complaint.product,
            issue=complaint.issue,
            sentiment=complaint.sentiment,
            category=complaint.category,
            urgency_score=complaint.urgency_score,
            churn_risk=complaint.churn_risk,
            confidence_scores=confidence_scores,
            processed_at=complaint.processed_at,
            ai_status=complaint.ai_status,
        )
