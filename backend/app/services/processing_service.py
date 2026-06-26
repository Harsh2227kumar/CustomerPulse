from datetime import UTC, datetime
import logging

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.pipelines.complaint_pipeline import (
    BedrockUnavailableError,
    ComplaintAIPipeline,
    InvalidAIOutputError,
    LocalSignals,
)
from app.ai.preprocessing.cleaner import clean_complaint_text
from app.ai.validators.review_router import review_reason_for
from app.compliance.engine import ComplianceEngine
from app.compliance.models import AIResponseFields, AISignals, ComplaintComplianceInput, SLAState
from app.compliance.service import ComplianceEvidenceService
from app.core.config import Settings
from app.core.constants import (
    ChurnRisk,
    ProcessingStatus,
    ProcessingTrigger,
    ReviewReason,
    WebSocketEvent,
)
from app.models.complaint import Complaint
from app.models.processing import ComplaintProcessingRun
from app.schemas.ai_response import (
    AIEnrichment,
    ConfidenceScores,
    ProcessedComplaintResponse,
    SimilarCaseEvidence,
)
from app.schemas.complaint import ComplaintProcessRequest
from app.services.embedding_service import EmbeddingService
from app.services.retrieval_service import SimilarComplaintService
from app.websocket.broadcaster import broadcast_processing_event


logger = logging.getLogger(__name__)
PUBLIC_PROCESSING_ERROR = "Complaint processing failed."


class ComplaintNotFoundError(LookupError):
    pass


class ProcessingService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.pipeline = ComplaintAIPipeline(settings)
        self.embeddings = EmbeddingService(settings.embedding_model)
        self.retrieval = SimilarComplaintService()

    async def process_complaint(
        self,
        db: AsyncSession,
        complaint_request: ComplaintProcessRequest,
        *,
        trigger: ProcessingTrigger = ProcessingTrigger.API_REQUEST,
        initiated_by: str | None = None,
    ) -> ProcessedComplaintResponse:
        complaint: Complaint | None = None
        run: ComplaintProcessingRun | None = None
        local: LocalSignals | None = None
        evidence: list[SimilarCaseEvidence] = []
        await self._emit_event(WebSocketEvent.RECEIVED, complaint_request.complaint_id)
        try:
            complaint = await self._get_or_create_complaint(db, complaint_request)
            complaint.ai_status = ProcessingStatus.PROCESSING.value
            complaint.error_message = None
            await db.flush()
            run = await self._start_processing_run(db, complaint, trigger, initiated_by)

            await self._emit_event(WebSocketEvent.PREPROCESSING, complaint_request.complaint_id)
            local = self.pipeline.run_local_layer(complaint_request)
            run.local_signals = self._local_signals_payload(local)
            await self._emit_event(
                WebSocketEvent.LOCAL_ML,
                complaint_request.complaint_id,
                {"urgency_score": local.urgency_score, "category": local.category},
            )

            embedding = await self.embeddings.embed_text(local.cleaned_narrative)
            evidence = await self.retrieval.retrieve(
                db,
                complaint,
                embedding,
                threshold=self.settings.similarity_threshold,
                limit=self.settings.similar_case_limit,
            )
            run.prompt_evidence = [case.model_dump(mode="json") for case in evidence]
            await self._emit_event(
                WebSocketEvent.BEDROCK_PROCESSING,
                complaint_request.complaint_id,
            )

            preset_reason: ReviewReason | None = None
            try:
                enrichment, _ = await self.pipeline.process(
                    complaint_request,
                    local=local,
                    similar_cases=evidence,
                )
            except BedrockUnavailableError:
                preset_reason = ReviewReason.BEDROCK_UNAVAILABLE_AFTER_RETRIES
                enrichment = self._fallback_enrichment(local, evidence)
            except InvalidAIOutputError:
                preset_reason = ReviewReason.INVALID_AI_OUTPUT
                enrichment = self._fallback_enrichment(local, evidence)

            await self._emit_event(WebSocketEvent.VALIDATING, complaint_request.complaint_id)
            reason = preset_reason or review_reason_for(enrichment)
            now = datetime.now(UTC)
            self._store_enrichment(complaint, enrichment, embedding, now)
            complaint.ai_status = (
                ProcessingStatus.HUMAN_REVIEW.value if reason else ProcessingStatus.COMPLETED.value
            )
            if reason:
                complaint.human_review_reason = reason.value
                complaint.human_review_created_at = now
            else:
                complaint.human_review_reason = None
                complaint.human_review_created_at = None
            run.status_outcome = complaint.ai_status
            run.ai_payload = enrichment.model_dump(mode="json")
            run.error_category = reason.value if reason else None
            run.finished_at = now
            await db.commit()
            await db.refresh(complaint)
            response = self._response(complaint, enrichment)
            await self._store_compliance_evidence(db, complaint, enrichment, now)

            if reason:
                await self._emit_event(
                    WebSocketEvent.HUMAN_REVIEW_REQUIRED,
                    complaint_request.complaint_id,
                    {
                        "status": complaint.ai_status,
                        "reason": reason.value,
                        "ai_confidence": enrichment.ai_confidence,
                        "next_action": enrichment.next_action,
                    },
                )
            else:
                await self._emit_event(
                    WebSocketEvent.SAVED,
                    complaint_request.complaint_id,
                    response.model_dump(mode="json"),
                )
            return response
        except Exception:
            logger.exception("Complaint processing failed for %s.", complaint_request.complaint_id)
            try:
                await db.rollback()
                complaint = await self._find_complaint(db, complaint_request.complaint_id)
                if complaint is None:
                    complaint = Complaint(
                        source_complaint_id=complaint_request.complaint_id,
                        narrative=complaint_request.narrative,
                        channel=complaint_request.channel,
                        product=complaint_request.product,
                        issue=complaint_request.issue,
                        company=complaint_request.company,
                    )
                    db.add(complaint)
                    await db.flush()
                complaint.ai_status = ProcessingStatus.FAILED.value
                complaint.retry_count += 1
                complaint.error_message = PUBLIC_PROCESSING_ERROR
                complaint.human_review_reason = None
                complaint.human_review_created_at = None
                run = await self._start_processing_run(db, complaint, trigger, initiated_by)
                if local is not None:
                    run.local_signals = self._local_signals_payload(local)
                run.prompt_evidence = [case.model_dump(mode="json") for case in evidence]
                run.status_outcome = ProcessingStatus.FAILED.value
                run.error_category = "unexpected_processing_failure"
                run.finished_at = datetime.now(UTC)
                await db.commit()
            except Exception:
                await db.rollback()
                logger.exception(
                    "Unable to persist failed processing outcome for %s.",
                    complaint_request.complaint_id,
                )
            await self._emit_event(
                WebSocketEvent.FAILED,
                complaint_request.complaint_id,
                {"error": PUBLIC_PROCESSING_ERROR},
            )
            raise

    async def process_imported_complaint(
        self,
        db: AsyncSession,
        complaint_id: str,
        *,
        trigger: ProcessingTrigger = ProcessingTrigger.IMPORTED_REQUEST,
        initiated_by: str | None = None,
    ) -> ProcessedComplaintResponse:
        complaint = await self._find_complaint(db, complaint_id)
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
            trigger=trigger,
            initiated_by=initiated_by,
        )

    async def embed_complaint(self, db: AsyncSession, complaint_id: str) -> Complaint:
        complaint = await self._find_complaint(db, complaint_id)
        if complaint is None:
            raise ComplaintNotFoundError(complaint_id)
        cleaned = clean_complaint_text(complaint.narrative)
        complaint.embedding = await self.embeddings.embed_text(cleaned.cleaned)
        complaint.embedding_model = self.settings.embedding_model
        complaint.embedded_at = datetime.now(UTC)
        await db.commit()
        return complaint

    async def _find_complaint(
        self,
        db: AsyncSession,
        complaint_id: str,
        *,
        lock: bool = False,
    ) -> Complaint | None:
        statement = select(Complaint).where(
            or_(Complaint.source_complaint_id == complaint_id, Complaint.id == complaint_id)
        )
        if lock:
            statement = statement.with_for_update()
        return (await db.execute(statement)).scalar_one_or_none()

    async def _get_or_create_complaint(
        self,
        db: AsyncSession,
        complaint_request: ComplaintProcessRequest,
    ) -> Complaint:
        complaint = await self._find_complaint(
            db, complaint_request.complaint_id, lock=True
        )
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

    async def _start_processing_run(
        self,
        db: AsyncSession,
        complaint: Complaint,
        trigger: ProcessingTrigger,
        initiated_by: str | None,
    ) -> ComplaintProcessingRun:
        prior_attempts = (
            await db.execute(
                select(func.count()).select_from(ComplaintProcessingRun).where(
                    ComplaintProcessingRun.complaint_id == complaint.id
                )
            )
        ).scalar_one()
        run = ComplaintProcessingRun(
            complaint_id=complaint.id,
            attempt_number=prior_attempts + 1,
            status_outcome=ProcessingStatus.PROCESSING.value,
            trigger_reason=trigger.value,
            initiated_by=initiated_by,
            bedrock_model=self.settings.bedrock_model,
        )
        db.add(run)
        await db.flush()
        return run

    def _store_enrichment(
        self,
        complaint: Complaint,
        enrichment: AIEnrichment,
        embedding: list[float],
        now: datetime,
    ) -> None:
        complaint.sentiment = enrichment.sentiment.value
        complaint.category = enrichment.category
        complaint.urgency_score = enrichment.urgency_score
        complaint.churn_risk = enrichment.churn_risk.value
        complaint.draft_response = enrichment.draft_response
        complaint.next_action = enrichment.next_action
        complaint.confidence_scores = enrichment.confidence_scores.model_dump()
        complaint.ai_confidence = enrichment.ai_confidence
        complaint.ai_reasoning = enrichment.ai_reasoning
        complaint.similar_case_evidence = [
            case.model_dump(mode="json") for case in enrichment.similar_cases
        ]
        complaint.embedding = embedding
        complaint.embedding_model = self.settings.embedding_model
        complaint.embedded_at = now
        complaint.processed_at = now
        complaint.error_message = None


    async def _store_compliance_evidence(
        self,
        db: AsyncSession,
        complaint: Complaint,
        enrichment: AIEnrichment,
        evaluated_at: datetime,
    ) -> None:
        try:
            compliance_input = self._compliance_input(complaint, enrichment, evaluated_at)
            result = ComplianceEngine().evaluate(compliance_input, evaluated_at=evaluated_at)
            evidence_service = ComplianceEvidenceService()
            _, existing_count = await evidence_service.list_records(
                db,
                limit=1,
                offset=0,
                complaint_id=result.complaint_id,
            )
            if existing_count:
                return
            await evidence_service.store_result(db, result, notes="auto-triggered-from-processing")
        except Exception:
            logger.exception(
                "Unable to store compliance evidence for complaint %s.",
                complaint.source_complaint_id or complaint.id,
            )

    def _compliance_input(
        self,
        complaint: Complaint,
        enrichment: AIEnrichment,
        evaluated_at: datetime,
    ) -> ComplaintComplianceInput:
        date_received = complaint.date_received or complaint.created_at or evaluated_at
        days_elapsed = max((evaluated_at.date() - date_received.date()).days, 0)
        resolved_at = complaint.processed_at if complaint.ai_status == ProcessingStatus.COMPLETED.value else None
        days_to_deadline = 30 - days_elapsed
        sla_breached = complaint.timely_response is False or (resolved_at is None and days_elapsed > 30)
        breach_risk_level = "critical" if sla_breached else "high" if resolved_at is None and days_to_deadline <= 2 else "low"

        return ComplaintComplianceInput(
            complaint_id=complaint.id,
            source_complaint_id=complaint.source_complaint_id,
            product=complaint.product,
            issue=complaint.issue,
            sub_issue=complaint.sub_issue,
            narrative=complaint.narrative,
            channel=complaint.channel,
            date_received=date_received,
            acknowledged_at=complaint.processed_at,
            resolved_at=resolved_at,
            ai_signals=AISignals(
                severity="high" if enrichment.urgency_score >= 70 else "medium",
                urgency_score=enrichment.urgency_score,
                key_issue=complaint.issue or enrichment.category,
                confidence=enrichment.ai_confidence,
            ),
            response_fields=AIResponseFields(
                category=enrichment.category,
                urgency_score=enrichment.urgency_score,
                draft_response=enrichment.draft_response,
                resolution=(
                    getattr(complaint, "approved_response", None)
                    or getattr(complaint, "review_resolution", None)
                    or enrichment.next_action
                ),
                next_action=enrichment.next_action,
                ai_confidence=enrichment.ai_confidence,
            ),
            sla=SLAState(
                is_breached=sla_breached,
                breach_risk_level=breach_risk_level,
                days_elapsed=days_elapsed,
                days_to_deadline=days_to_deadline,
            ),
        )

    def _fallback_enrichment(self, local: LocalSignals, evidence: list) -> AIEnrichment:
        return AIEnrichment(
            sentiment=local.sentiment,
            category=local.category,
            urgency_score=local.urgency_score,
            churn_risk=ChurnRisk.HIGH if local.urgency_score > 70 else ChurnRisk.MEDIUM,
            draft_response="",
            next_action="Manual agent review required for this complaint.",
            similar_cases=evidence,
            confidence_scores=ConfidenceScores(
                sentiment=round(local.sentiment_confidence * 100),
                category=round(local.category_confidence * 100),
                urgency=round(local.urgency_confidence * 100),
            ),
            ai_confidence=local.combined_confidence,
            ai_reasoning="Automated enrichment unavailable; local signals preserved for review.",
        )

    def _local_signals_payload(self, local: LocalSignals) -> dict:
        return {
            "sentiment": local.sentiment.value,
            "sentiment_confidence": local.sentiment_confidence,
            "category": local.category,
            "category_confidence": local.category_confidence,
            "urgency_score": local.urgency_score,
            "urgency_confidence": local.urgency_confidence,
            "combined_confidence": local.combined_confidence,
        }

    def _response(
        self, complaint: Complaint, enrichment: AIEnrichment
    ) -> ProcessedComplaintResponse:
        return ProcessedComplaintResponse(
            complaint_id=complaint.source_complaint_id or complaint.id,
            narrative=complaint.narrative,
            channel=complaint.channel,
            processed_at=complaint.processed_at.isoformat() if complaint.processed_at else "",
            ai_status=complaint.ai_status,
            human_review_reason=complaint.human_review_reason,
            human_review_created_at=(
                complaint.human_review_created_at.isoformat()
                if complaint.human_review_created_at
                else None
            ),
            **enrichment.model_dump(),
        )

    async def _emit_event(
        self,
        event: WebSocketEvent,
        complaint_id: str,
        data: dict | None = None,
    ) -> None:
        try:
            await broadcast_processing_event(event, complaint_id, data)
        except Exception:
            logger.exception(
                "Unable to broadcast %s event for complaint %s.",
                event.value,
                complaint_id,
            )
