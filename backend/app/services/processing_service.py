from datetime import UTC, datetime
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.pipelines.complaint_pipeline import ComplaintAIPipeline
from app.core.config import Settings
from app.core.constants import ProcessingStatus, WebSocketEvent
from app.models.complaint import Complaint
from app.schemas.ai_response import ProcessedComplaintResponse
from app.schemas.complaint import ComplaintProcessRequest
from app.websocket.broadcaster import broadcast_processing_event


logger = logging.getLogger(__name__)
PUBLIC_PROCESSING_ERROR = "Complaint processing failed."


class ComplaintNotFoundError(LookupError):
    pass


class ProcessingService:
    def __init__(self, settings: Settings):
        self.pipeline = ComplaintAIPipeline(settings)

    async def process_complaint(
        self,
        db: AsyncSession,
        complaint_request: ComplaintProcessRequest,
    ) -> ProcessedComplaintResponse:
        await broadcast_processing_event(WebSocketEvent.RECEIVED, complaint_request.complaint_id)
        complaint = await self._get_or_create_complaint(db, complaint_request)
        complaint.ai_status = ProcessingStatus.PROCESSING.value
        await db.flush()

        try:
            await broadcast_processing_event(WebSocketEvent.PREPROCESSING, complaint_request.complaint_id)
            local_signals = self.pipeline.run_local_layer(complaint_request)
            await broadcast_processing_event(
                WebSocketEvent.LOCAL_ML,
                complaint_request.complaint_id,
                {"urgency_score": local_signals.urgency_score, "category": local_signals.category},
            )
            await broadcast_processing_event(
                WebSocketEvent.BEDROCK_PROCESSING,
                complaint_request.complaint_id,
            )
            enrichment, _ = await self.pipeline.process(complaint_request)
            await broadcast_processing_event(WebSocketEvent.VALIDATING, complaint_request.complaint_id)

            now = datetime.now(UTC)
            complaint.sentiment = enrichment.sentiment.value
            complaint.category = enrichment.category
            complaint.urgency_score = enrichment.urgency_score
            complaint.churn_risk = enrichment.churn_risk.value
            complaint.draft_response = enrichment.draft_response
            complaint.next_action = enrichment.next_action
            complaint.confidence_scores = enrichment.confidence_scores.model_dump()
            complaint.ai_confidence = enrichment.ai_confidence
            complaint.ai_reasoning = enrichment.ai_reasoning
            complaint.processed_at = now
            complaint.ai_status = ProcessingStatus.COMPLETED.value
            complaint.error_message = None
            await db.commit()
            await db.refresh(complaint)
            response = ProcessedComplaintResponse(
                complaint_id=complaint_request.complaint_id,
                narrative=complaint.narrative,
                channel=complaint.channel,
                processed_at=now.isoformat(),
                **enrichment.model_dump(),
            )
            await broadcast_processing_event(
                WebSocketEvent.SAVED,
                complaint_request.complaint_id,
                response.model_dump(mode="json"),
            )
            return response
        except Exception as exc:
            logger.exception("Complaint processing failed for %s.", complaint_request.complaint_id)
            complaint.ai_status = ProcessingStatus.FAILED.value
            complaint.retry_count += 1
            complaint.error_message = PUBLIC_PROCESSING_ERROR
            await db.commit()
            await broadcast_processing_event(
                WebSocketEvent.FAILED,
                complaint_request.complaint_id,
                {"error": PUBLIC_PROCESSING_ERROR},
            )
            raise

    async def process_imported_complaint(
        self,
        db: AsyncSession,
        complaint_id: str,
    ) -> ProcessedComplaintResponse:
        result = await db.execute(
            select(Complaint).where(Complaint.source_complaint_id == complaint_id)
        )
        complaint = result.scalar_one_or_none()
        if complaint is None:
            raise ComplaintNotFoundError(complaint_id)
        return await self.process_complaint(
            db,
            ComplaintProcessRequest(
                complaint_id=complaint.source_complaint_id or complaint.id,
                narrative=complaint.narrative,
                channel=complaint.channel,
                product=complaint.product,
                issue=complaint.issue,
                company=complaint.company,
            ),
        )

    async def _get_or_create_complaint(
        self,
        db: AsyncSession,
        complaint_request: ComplaintProcessRequest,
    ) -> Complaint:
        stmt = select(Complaint).where(Complaint.source_complaint_id == complaint_request.complaint_id)
        result = await db.execute(stmt)
        complaint = result.scalar_one_or_none()
        if complaint:
            complaint.narrative = complaint_request.narrative
            complaint.channel = complaint_request.channel
            complaint.product = complaint_request.product
            complaint.issue = complaint_request.issue
            complaint.company = complaint_request.company
            return complaint
        complaint = Complaint(
            source_complaint_id=complaint_request.complaint_id,
            narrative=complaint_request.narrative,
            channel=complaint_request.channel,
            product=complaint_request.product,
            issue=complaint_request.issue,
            company=complaint_request.company,
        )
        db.add(complaint)
        return complaint
