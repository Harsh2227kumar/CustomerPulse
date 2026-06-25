from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import ChurnRisk, ProcessingStatus
from app.exports.schemas.export_schemas import (
    AnalyticsCSVExportQuery,
    ComplaintCSVExportQuery,
    ComplaintPDFExportQuery,
    FeedbackCSVExportQuery,
)
from app.feedback.models import AgentFeedback
from app.models.complaint import Complaint


class ExportRepository:
    COMPLAINT_EXPORT_LIMIT = 5000
    FEEDBACK_EXPORT_LIMIT = 2000

    async def stream_complaints(
        self,
        db: AsyncSession,
        filters: ComplaintCSVExportQuery,
    ) -> AsyncIterator[dict[str, Any]]:
        complaint_id = case(
            (Complaint.source_complaint_id.is_not(None), Complaint.source_complaint_id),
            else_=Complaint.id,
        ).label("complaint_id")
        stmt = (
            select(
                complaint_id,
                Complaint.narrative.label("narrative"),
                Complaint.channel.label("channel"),
                Complaint.product.label("product"),
                Complaint.sub_product.label("sub_product"),
                Complaint.issue.label("issue"),
                Complaint.sub_issue.label("sub_issue"),
                Complaint.company.label("company"),
                Complaint.company_response.label("company_response"),
                Complaint.timely_response.label("timely_response"),
                Complaint.date_received.label("date_received"),
                Complaint.sentiment.label("sentiment"),
                Complaint.category.label("category"),
                Complaint.urgency_score.label("urgency_score"),
                Complaint.churn_risk.label("churn_risk"),
                Complaint.draft_response.label("draft_response"),
                Complaint.next_action.label("next_action"),
                Complaint.ai_confidence.label("ai_confidence"),
                Complaint.ai_status.label("ai_status"),
                Complaint.processed_at.label("processed_at"),
                Complaint.created_at.label("created_at"),
            )
            .order_by(Complaint.created_at.asc(), Complaint.id.asc())
            .limit(min(filters.limit, self.COMPLAINT_EXPORT_LIMIT))
        )
        stmt = self._apply_complaint_filters(stmt, filters)
        result = await db.stream(stmt)
        async for row in result.mappings():
            yield dict(row)

    async def stream_regulatory_complaints(
        self,
        db: AsyncSession,
        filters: ComplaintCSVExportQuery,
    ) -> AsyncIterator[dict[str, Any]]:
        complaint_id = case(
            (Complaint.source_complaint_id.is_not(None), Complaint.source_complaint_id),
            else_=Complaint.id,
        ).label("complaint_id")
        stmt = (
            select(
                complaint_id,
                Complaint.narrative.label("narrative"),
                Complaint.channel.label("channel"),
                Complaint.product.label("product"),
                Complaint.sub_product.label("sub_product"),
                Complaint.issue.label("issue"),
                Complaint.sub_issue.label("sub_issue"),
                Complaint.company.label("company"),
                Complaint.company_response.label("company_response"),
                Complaint.timely_response.label("timely_response"),
                Complaint.date_received.label("date_received"),
                Complaint.sentiment.label("sentiment"),
                Complaint.category.label("category"),
                Complaint.urgency_score.label("urgency_score"),
                Complaint.churn_risk.label("churn_risk"),
                Complaint.draft_response.label("draft_response"),
                Complaint.next_action.label("next_action"),
                Complaint.ai_confidence.label("ai_confidence"),
                Complaint.ai_status.label("ai_status"),
                Complaint.human_review_reason.label("human_review_reason"),
                Complaint.reviewer.label("reviewer"),
                Complaint.review_resolution.label("review_resolution"),
                Complaint.review_notes.label("review_notes"),
                Complaint.reviewed_at.label("reviewed_at"),
                Complaint.processed_at.label("processed_at"),
                Complaint.created_at.label("created_at"),
            )
            .order_by(Complaint.created_at.asc(), Complaint.id.asc())
            .limit(min(filters.limit, self.COMPLAINT_EXPORT_LIMIT))
        )
        stmt = self._apply_complaint_filters(stmt, filters)
        result = await db.stream(stmt)
        async for row in result.mappings():
            yield dict(row)


    async def stream_feedback(
        self,
        db: AsyncSession,
        filters: FeedbackCSVExportQuery,
    ) -> AsyncIterator[dict[str, Any]]:
        complaint_id = case(
            (Complaint.source_complaint_id.is_not(None), Complaint.source_complaint_id),
            else_=Complaint.id,
        ).label("complaint_id")
        stmt = (
            select(
                AgentFeedback.id.label("feedback_id"),
                complaint_id,
                AgentFeedback.feedback_action.label("action_type"),
                Complaint.draft_response.label("original_draft_response"),
                AgentFeedback.final_response.label("final_response"),
                AgentFeedback.action_used.label("action_used"),
                AgentFeedback.human_review_outcome.label("human_review_outcome"),
                AgentFeedback.similar_cases_useful.label("similar_case_useful"),
                AgentFeedback.submitted_at.label("created_at"),
            )
            .join(Complaint, Complaint.id == AgentFeedback.complaint_pk)
            .order_by(AgentFeedback.submitted_at.asc(), AgentFeedback.id.asc())
            .limit(min(filters.limit, self.FEEDBACK_EXPORT_LIMIT))
        )
        if filters.date_from is not None:
            stmt = stmt.where(AgentFeedback.submitted_at >= filters.date_from)
        if filters.date_to is not None:
            stmt = stmt.where(AgentFeedback.submitted_at <= filters.date_to)
        if filters.action_type is not None:
            stmt = stmt.where(AgentFeedback.feedback_action == filters.action_type.value)
        result = await db.stream(stmt)
        async for row in result.mappings():
            yield dict(row)

    async def get_analytics_export_rows(
        self,
        db: AsyncSession,
        filters: AnalyticsCSVExportQuery,
    ) -> list[dict[str, Any]]:
        timely_rate = func.avg(
            case(
                (Complaint.timely_response.is_(True), 100.0),
                (Complaint.timely_response.is_(False), 0.0),
                else_=None,
            )
        )
        high_churn_count = func.sum(
            case((Complaint.churn_risk == ChurnRisk.HIGH.value, 1), else_=0)
        )
        stmt = (
            select(
                Complaint.product.label("product"),
                Complaint.channel.label("channel"),
                Complaint.sentiment.label("sentiment"),
                func.count(Complaint.id).label("total_complaints"),
                func.avg(Complaint.urgency_score).label("avg_urgency"),
                timely_rate.label("timely_rate_pct"),
                high_churn_count.label("high_churn_count"),
            )
            .where(Complaint.ai_status == ProcessingStatus.COMPLETED.value)
            .group_by(Complaint.product, Complaint.channel, Complaint.sentiment)
            .order_by(
                func.count(Complaint.id).desc(),
                Complaint.product.asc(),
                Complaint.channel.asc(),
                Complaint.sentiment.asc(),
            )
        )
        stmt = self._apply_pdf_filters(stmt, filters.date_from, filters.date_to, None, None)
        rows = (await db.execute(stmt)).mappings().all()
        return [dict(row) for row in rows]

    async def get_pdf_summary(
        self,
        db: AsyncSession,
        filters: ComplaintPDFExportQuery,
    ) -> dict[str, Any]:
        avg_urgency = func.avg(
            case(
                (Complaint.ai_status == ProcessingStatus.COMPLETED.value, Complaint.urgency_score),
                else_=None,
            )
        )
        timely_rate = func.avg(
            case(
                (
                    (Complaint.ai_status == ProcessingStatus.COMPLETED.value)
                    & Complaint.timely_response.is_(True),
                    100.0,
                ),
                (
                    (Complaint.ai_status == ProcessingStatus.COMPLETED.value)
                    & Complaint.timely_response.is_(False),
                    0.0,
                ),
                else_=None,
            )
        )
        high_churn_count = func.sum(
            case(
                (
                    (Complaint.ai_status == ProcessingStatus.COMPLETED.value)
                    & (Complaint.churn_risk == ChurnRisk.HIGH.value),
                    1,
                ),
                else_=0,
            )
        )
        stmt = select(
            func.count(Complaint.id).label("total_complaints"),
            func.sum(
                case((Complaint.ai_status == ProcessingStatus.COMPLETED.value, 1), else_=0)
            ).label("completed_count"),
            func.sum(
                case((Complaint.ai_status == ProcessingStatus.PENDING.value, 1), else_=0)
            ).label("pending_count"),
            func.sum(
                case((Complaint.ai_status == ProcessingStatus.FAILED.value, 1), else_=0)
            ).label("failed_count"),
            avg_urgency.label("avg_urgency_score"),
            timely_rate.label("timely_response_pct"),
            high_churn_count.label("high_churn_risk_count"),
        )
        stmt = self._apply_pdf_filters(stmt, filters.date_from, filters.date_to, filters.product, filters.channel)
        row = (await db.execute(stmt)).mappings().one()
        return dict(row)

    async def get_sentiment_distribution(
        self,
        db: AsyncSession,
        filters: ComplaintPDFExportQuery,
    ) -> list[dict[str, Any]]:
        total_stmt = select(func.count(Complaint.id)).where(
            Complaint.ai_status == ProcessingStatus.COMPLETED.value
        )
        total_stmt = self._apply_pdf_filters(
            total_stmt,
            filters.date_from,
            filters.date_to,
            filters.product,
            filters.channel,
        )
        total = (await db.execute(total_stmt)).scalar_one()

        stmt = (
            select(
                Complaint.sentiment.label("sentiment"),
                func.count(Complaint.id).label("count"),
            )
            .where(Complaint.ai_status == ProcessingStatus.COMPLETED.value)
            .group_by(Complaint.sentiment)
            .order_by(Complaint.sentiment.asc())
        )
        stmt = self._apply_pdf_filters(stmt, filters.date_from, filters.date_to, filters.product, filters.channel)
        rows = (await db.execute(stmt)).mappings().all()
        indexed = {row["sentiment"]: int(row["count"]) for row in rows}
        sentiments = ("Positive", "Neutral", "Negative")
        return [
            {
                "sentiment": sentiment,
                "count": indexed.get(sentiment, 0),
                "percentage": (indexed.get(sentiment, 0) / total * 100.0) if total else 0.0,
            }
            for sentiment in sentiments
        ]

    async def get_top_products(
        self,
        db: AsyncSession,
        filters: ComplaintPDFExportQuery,
    ) -> list[dict[str, Any]]:
        timely_rate = func.avg(
            case(
                (Complaint.timely_response.is_(True), 100.0),
                (Complaint.timely_response.is_(False), 0.0),
                else_=None,
            )
        )
        stmt = (
            select(
                Complaint.product.label("product"),
                func.count(Complaint.id).label("count"),
                timely_rate.label("timely_rate_pct"),
                func.avg(Complaint.urgency_score).label("avg_urgency"),
            )
            .where(Complaint.ai_status == ProcessingStatus.COMPLETED.value)
            .group_by(Complaint.product)
            .order_by(func.count(Complaint.id).desc(), Complaint.product.asc())
            .limit(10)
        )
        stmt = self._apply_pdf_filters(stmt, filters.date_from, filters.date_to, filters.product, filters.channel)
        return [dict(row) for row in (await db.execute(stmt)).mappings().all()]

    async def get_top_channels(
        self,
        db: AsyncSession,
        filters: ComplaintPDFExportQuery,
    ) -> list[dict[str, Any]]:
        timely_rate = func.avg(
            case(
                (Complaint.timely_response.is_(True), 100.0),
                (Complaint.timely_response.is_(False), 0.0),
                else_=None,
            )
        )
        stmt = (
            select(
                Complaint.channel.label("channel"),
                func.count(Complaint.id).label("count"),
                timely_rate.label("timely_rate_pct"),
            )
            .where(Complaint.ai_status == ProcessingStatus.COMPLETED.value)
            .group_by(Complaint.channel)
            .order_by(func.count(Complaint.id).desc(), Complaint.channel.asc())
            .limit(5)
        )
        stmt = self._apply_pdf_filters(stmt, filters.date_from, filters.date_to, filters.product, filters.channel)
        return [dict(row) for row in (await db.execute(stmt)).mappings().all()]

    async def get_urgency_distribution(
        self,
        db: AsyncSession,
        filters: ComplaintPDFExportQuery,
    ) -> list[dict[str, Any]]:
        bucket = case(
            (Complaint.urgency_score.is_(None), "Unscored"),
            (Complaint.urgency_score <= 25, "Low"),
            (Complaint.urgency_score <= 50, "Medium"),
            (Complaint.urgency_score <= 75, "High"),
            else_="Critical",
        ).label("bucket")
        sort_order = case(
            (bucket == "Low", 1),
            (bucket == "Medium", 2),
            (bucket == "High", 3),
            (bucket == "Critical", 4),
            else_=5,
        )
        stmt = (
            select(
                bucket,
                func.count(Complaint.id).label("count"),
            )
            .where(Complaint.ai_status == ProcessingStatus.COMPLETED.value)
            .group_by(bucket)
            .order_by(sort_order.asc())
        )
        stmt = self._apply_pdf_filters(stmt, filters.date_from, filters.date_to, filters.product, filters.channel)
        rows = [dict(row) for row in (await db.execute(stmt)).mappings().all()]
        counts = {row["bucket"]: row["count"] for row in rows}
        return [
            {"bucket": "Low", "count": int(counts.get("Low", 0))},
            {"bucket": "Medium", "count": int(counts.get("Medium", 0))},
            {"bucket": "High", "count": int(counts.get("High", 0))},
            {"bucket": "Critical", "count": int(counts.get("Critical", 0))},
        ]

    async def get_churn_risk_summary(
        self,
        db: AsyncSession,
        filters: ComplaintPDFExportQuery,
    ) -> list[dict[str, Any]]:
        stmt = (
            select(
                Complaint.churn_risk.label("churn_risk"),
                func.count(Complaint.id).label("count"),
            )
            .where(Complaint.ai_status == ProcessingStatus.COMPLETED.value)
            .group_by(Complaint.churn_risk)
            .order_by(Complaint.churn_risk.asc())
        )
        stmt = self._apply_pdf_filters(stmt, filters.date_from, filters.date_to, filters.product, filters.channel)
        rows = [dict(row) for row in (await db.execute(stmt)).mappings().all()]
        counts = {row["churn_risk"]: row["count"] for row in rows}
        return [
            {"churn_risk": "Low", "count": int(counts.get("Low", 0))},
            {"churn_risk": "Medium", "count": int(counts.get("Medium", 0))},
            {"churn_risk": "High", "count": int(counts.get("High", 0))},
        ]

    def _apply_complaint_filters(self, stmt, filters: ComplaintCSVExportQuery):
        if filters.date_from is not None:
            stmt = stmt.where(Complaint.date_received >= filters.date_from)
        if filters.date_to is not None:
            stmt = stmt.where(Complaint.date_received <= filters.date_to)
        if filters.product:
            stmt = stmt.where(Complaint.product == filters.product)
        if filters.channel:
            stmt = stmt.where(Complaint.channel == filters.channel)
        if filters.sentiment:
            stmt = stmt.where(Complaint.sentiment == filters.sentiment.value)
        if filters.urgency_min is not None:
            stmt = stmt.where(Complaint.urgency_score >= filters.urgency_min)
        if filters.urgency_max is not None:
            stmt = stmt.where(Complaint.urgency_score <= filters.urgency_max)
        if filters.churn_risk:
            stmt = stmt.where(Complaint.churn_risk == filters.churn_risk.value)
        if filters.ai_status:
            stmt = stmt.where(Complaint.ai_status == filters.ai_status.value)
        return stmt

    def _apply_pdf_filters(
        self,
        stmt,
        date_from: datetime | None,
        date_to: datetime | None,
        product: str | None,
        channel: str | None,
    ):
        if date_from is not None:
            stmt = stmt.where(Complaint.date_received >= date_from)
        if date_to is not None:
            stmt = stmt.where(Complaint.date_received <= date_to)
        if product:
            stmt = stmt.where(Complaint.product == product)
        if channel:
            stmt = stmt.where(Complaint.channel == channel)
        return stmt


    async def get_regulatory_summary(
        self,
        db: AsyncSession,
        filters: ComplaintPDFExportQuery,
    ) -> dict[str, Any]:
        stmt = select(
            func.count(Complaint.id).label("total_complaints"),
            func.sum(
                case((Complaint.ai_status == ProcessingStatus.COMPLETED.value, 1), else_=0)
            ).label("completed_count"),
            func.sum(
                case((Complaint.reviewed_at.is_not(None), 1), else_=0)
            ).label("reviewed_count"),
            func.sum(
                case((Complaint.human_review_reason.is_not(None), 1), else_=0)
            ).label("escalated_count"),
            func.avg(Complaint.urgency_score).label("avg_urgency_score"),
            func.avg(
                case(
                    (Complaint.timely_response.is_(True), 100.0),
                    (Complaint.timely_response.is_(False), 0.0),
                    else_=None,
                )
            ).label("timely_response_pct")
        )
        stmt = self._apply_pdf_filters(stmt, filters.date_from, filters.date_to, filters.product, filters.channel)
        row = (await db.execute(stmt)).mappings().one()
        return dict(row)

    async def get_regulatory_complaints_list(
        self,
        db: AsyncSession,
        filters: ComplaintPDFExportQuery,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        complaint_id = case(
            (Complaint.source_complaint_id.is_not(None), Complaint.source_complaint_id),
            else_=Complaint.id,
        ).label("complaint_id")
        stmt = select(
            complaint_id,
            Complaint.product,
            Complaint.timely_response,
            Complaint.urgency_score,
            Complaint.reviewer,
            Complaint.review_resolution,
            Complaint.review_notes,
            Complaint.reviewed_at,
            Complaint.human_review_reason
        ).order_by(Complaint.created_at.desc()).limit(limit)
        stmt = self._apply_pdf_filters(stmt, filters.date_from, filters.date_to, filters.product, filters.channel)
        rows = (await db.execute(stmt)).mappings().all()
        return [dict(row) for row in rows]


