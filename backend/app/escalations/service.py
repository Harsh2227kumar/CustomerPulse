from datetime import datetime, UTC
import logging

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import (
    ChurnRisk,
    HIGH_URGENCY_REVIEW_THRESHOLD,
    ProcessingStatus,
    ReviewReason,
)
from app.escalations.models import Escalation
from app.escalations.repository import EscalationRepository
from app.escalations.schemas import (
    EscalationCreateRequest,
    EscalationListQuery,
    EscalationListResponse,
    EscalationRead,
    EscalationResolveRequest,
)
from app.models.complaint import Complaint
from app.sla.services.sla_service import SLAService

logger = logging.getLogger(__name__)


class EscalationNotFoundError(LookupError):
    pass

class EscalationComplaintNotFoundError(LookupError):
    pass

class EscalationAlreadyOpenError(ValueError):
    pass


class EscalationService:
    def __init__(self, repository: EscalationRepository | None = None) -> None:
        self.repository = repository or EscalationRepository()

    async def _resolve_complaint(self, db: AsyncSession, complaint_id: str) -> Complaint:
        stmt = select(Complaint).where(
            or_(Complaint.source_complaint_id == complaint_id, Complaint.id == complaint_id)
        )
        complaint = (await db.execute(stmt)).scalar_one_or_none()
        if complaint is None:
            raise EscalationComplaintNotFoundError(complaint_id)
        return complaint

    def _to_read_schema(self, escalation: Escalation, complaint: Complaint | None = None) -> EscalationRead:
        # Resolve display complaint_id if complaint is available, otherwise fallback to pk
        complaint_id = escalation.complaint_pk
        if complaint:
            complaint_id = complaint.source_complaint_id or complaint.id

        return EscalationRead(
            id=escalation.id,
            complaint_id=complaint_id,
            status=escalation.status,
            trigger_type=escalation.trigger_type,
            reason=escalation.reason,
            urgency_score_snapshot=escalation.urgency_score_snapshot,
            churn_risk_snapshot=escalation.churn_risk_snapshot,
            ai_confidence_snapshot=escalation.ai_confidence_snapshot,
            escalated_by=escalation.escalated_by,
            escalated_at=escalation.escalated_at,
            resolved_by=escalation.resolved_by,
            resolved_at=escalation.resolved_at,
            resolution_notes=escalation.resolution_notes,
            created_at=escalation.created_at,
            updated_at=escalation.updated_at,
        )

    async def escalate_manual(
        self,
        db: AsyncSession,
        complaint_id: str,
        payload: EscalationCreateRequest,
        actor: str,
    ) -> EscalationRead:
        complaint = await self._resolve_complaint(db, complaint_id)
        
        open_escalation = await self.repository.get_open_for_complaint(db, complaint.id)
        if open_escalation is not None:
            raise EscalationAlreadyOpenError("An open escalation already exists for this complaint.")

        snapshot = {
            "urgency_score": complaint.urgency_score,
            "churn_risk": complaint.churn_risk.value if complaint.churn_risk else None,
            "ai_confidence": complaint.ai_confidence,
        }

        try:
            escalation = await self.repository.create(
                db,
                complaint_pk=complaint.id,
                trigger_type="manual",
                reason=payload.reason,
                escalated_by=actor,
                snapshot=snapshot,
            )
            await db.commit()
            await db.refresh(escalation)
        except Exception:
            await db.rollback()
            raise

        try:
            from app.communications.service import CommunicationService
            await CommunicationService().add_escalation_note(
                db,
                complaint_pk=complaint.id,
                message=f"Escalated by {actor}: {payload.reason}",
                actor=actor,
            )
        except Exception:
            logger.exception("Failed to add communication note for manual escalation.")

        return self._to_read_schema(escalation, complaint)

    async def resolve(
        self,
        db: AsyncSession,
        escalation_id: str,
        payload: EscalationResolveRequest,
        actor: str,
    ) -> EscalationRead:
        escalation = await self.repository.get(db, escalation_id)
        if escalation is None:
            raise EscalationNotFoundError(escalation_id)

        try:
            escalation = await self.repository.resolve(
                db,
                escalation,
                resolved_by=actor,
                resolution_notes=payload.resolution_notes,
            )
            await db.commit()
            await db.refresh(escalation)
        except Exception:
            await db.rollback()
            raise

        complaint = await db.get(Complaint, escalation.complaint_pk)

        try:
            from app.communications.service import CommunicationService
            await CommunicationService().add_escalation_note(
                db,
                complaint_pk=escalation.complaint_pk,
                message=f"Escalation resolved by {actor}: {payload.resolution_notes}",
                actor=actor,
            )
        except Exception:
            logger.exception("Failed to add communication note for escalation resolution.")

        return self._to_read_schema(escalation, complaint)

    async def count_by_status(self, db: AsyncSession) -> dict[str, int]:
        return await self.repository.count_by_status(db)

    async def list_escalations(
        self,
        db: AsyncSession,
        filters: EscalationListQuery,
    ) -> EscalationListResponse:
        items, total = await self.repository.list(
            db,
            status=filters.status,
            trigger_type=filters.trigger_type,
            limit=filters.limit,
            offset=filters.offset,
        )
        
        # Resolve complaints for display IDs
        complaint_pks = list({item.complaint_pk for item in items})
        complaints = {}
        if complaint_pks:
            stmt = select(Complaint).where(Complaint.id.in_(complaint_pks))
            complaint_rows = (await db.execute(stmt)).scalars().all()
            complaints = {c.id: c for c in complaint_rows}

        read_items = [self._to_read_schema(item, complaints.get(item.complaint_pk)) for item in items]

        return EscalationListResponse(
            items=read_items,
            total=total,
            limit=filters.limit,
            offset=filters.offset,
        )

    async def get_escalation(self, db: AsyncSession, escalation_id: str) -> EscalationRead:
        escalation = await self.repository.get(db, escalation_id)
        if escalation is None:
            raise EscalationNotFoundError(escalation_id)
        
        complaint = await db.get(Complaint, escalation.complaint_pk)
        return self._to_read_schema(escalation, complaint)

    # Extension point for Member 2: once app/compliance/ exists and Complaint has a
    # compliance_flags column, add a check here — do not duplicate compliance logic,
    # just reference the flag.
    async def evaluate_auto_escalation(
        self,
        db: AsyncSession,
        complaint: Complaint,
    ) -> EscalationRead | None:
        if complaint.ai_status not in (
            ProcessingStatus.COMPLETED.value,
            ProcessingStatus.HUMAN_REVIEW.value,
        ):
            return None

        open_escalation = await self.repository.get_open_for_complaint(db, complaint.id)
        if open_escalation is not None:
            return None

        reasons: list[str] = []

        if (
            complaint.urgency_score is not None
            and complaint.urgency_score >= HIGH_URGENCY_REVIEW_THRESHOLD
            and complaint.churn_risk == ChurnRisk.HIGH.value
        ):
            reasons.append(f"urgency {complaint.urgency_score} with High churn risk")

        if complaint.human_review_reason in (
            ReviewReason.HIGH_RISK_HIGH_URGENCY.value,
            ReviewReason.BEDROCK_UNAVAILABLE_AFTER_RETRIES.value,
        ):
            reasons.append(f"flagged for human review: {complaint.human_review_reason}")

        if await SLAService().is_breach_risk(db, complaint.id):
            reasons.append("SLA breach risk")

        if not reasons:
            return None

        reason = "; ".join(reasons)
        snapshot = {
            "urgency_score": complaint.urgency_score,
            "churn_risk": complaint.churn_risk,
            "ai_confidence": complaint.ai_confidence,
        }

        try:
            escalation = await self.repository.create(
                db,
                complaint_pk=complaint.id,
                trigger_type="auto",
                reason=reason,
                escalated_by=None,
                snapshot=snapshot,
            )
            await db.commit()
            await db.refresh(escalation)
        except Exception:
            await db.rollback()
            raise

        try:
            from app.communications.service import CommunicationService
            await CommunicationService().add_escalation_note(
                db,
                complaint_pk=complaint.id,
                message=f"Auto-escalated: {reason}",
                actor="system",
            )
        except Exception:
            logger.exception("Failed to add communication note for auto-escalation.")

        return self._to_read_schema(escalation, complaint)
