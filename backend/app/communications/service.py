import logging

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.communications.repository import CommunicationRepository
from app.communications.schemas import (
    CommunicationEntryCreate,
    CommunicationEntryRead,
    TimelineResponse,
)
from app.models.complaint import Complaint

logger = logging.getLogger(__name__)


class CommunicationComplaintNotFoundError(LookupError):
    pass


class CommunicationService:
    def __init__(self, repository: CommunicationRepository | None = None) -> None:
        self.repository = repository or CommunicationRepository()

    async def resolve_complaint_pk(self, db: AsyncSession, complaint_id: str) -> str:
        stmt = select(Complaint.id).where(
            or_(Complaint.source_complaint_id == complaint_id, Complaint.id == complaint_id)
        )
        pk = (await db.execute(stmt)).scalar_one_or_none()
        if pk is None:
            raise CommunicationComplaintNotFoundError(complaint_id)
        return pk

    async def record_system_event(
        self,
        db: AsyncSession,
        complaint_pk: str,
        event_code: str,
        message: str,
        context: dict | None = None,
    ) -> None:
        try:
            await self.repository.create_entry(
                db,
                complaint_pk=complaint_pk,
                entry_type="system",
                event_code=event_code,
                message=message,
                actor="system",
                context=context,
            )
            await db.commit()
        except Exception:
            await db.rollback()
            logger.exception("Failed to record system event %s for complaint %s", event_code, complaint_pk)

    async def add_note(
        self,
        db: AsyncSession,
        complaint_id: str,
        payload: CommunicationEntryCreate,
        actor: str,
    ) -> CommunicationEntryRead:
        complaint_pk = await self.resolve_complaint_pk(db, complaint_id)
        try:
            entry = await self.repository.create_entry(
                db,
                complaint_pk=complaint_pk,
                entry_type=payload.entry_type,
                event_code=None,
                message=payload.message,
                actor=actor,
                context=None,
            )
            await db.commit()
            await db.refresh(entry)
        except Exception:
            await db.rollback()
            raise

        return CommunicationEntryRead(
            id=entry.id,
            complaint_id=complaint_id,
            entry_type=entry.entry_type,
            event_code=entry.event_code,
            message=entry.message,
            actor=entry.actor,
            context=entry.context,
            created_at=entry.created_at,
        )

    async def add_escalation_note(
        self,
        db: AsyncSession,
        complaint_pk: str,
        message: str,
        actor: str | None,
    ) -> CommunicationEntryRead:
        try:
            entry = await self.repository.create_entry(
                db,
                complaint_pk=complaint_pk,
                entry_type="escalation",
                event_code=None,
                message=message,
                actor=actor,
                context=None,
            )
            await db.commit()
            await db.refresh(entry)
        except Exception:
            await db.rollback()
            raise

        stmt = select(Complaint.source_complaint_id).where(Complaint.id == complaint_pk)
        source_id = (await db.execute(stmt)).scalar_one_or_none()
        resolved_id = source_id or complaint_pk

        return CommunicationEntryRead(
            id=entry.id,
            complaint_id=resolved_id,
            entry_type=entry.entry_type,
            event_code=entry.event_code,
            message=entry.message,
            actor=entry.actor,
            context=entry.context,
            created_at=entry.created_at,
        )

    async def get_timeline(self, db: AsyncSession, complaint_id: str) -> TimelineResponse:
        complaint_pk = await self.resolve_complaint_pk(db, complaint_id)
        entries = await self.repository.list_for_complaint(db, complaint_pk)
        return TimelineResponse(
            complaint_id=complaint_id,
            items=[
                CommunicationEntryRead(
                    id=e.id,
                    complaint_id=complaint_id,
                    entry_type=e.entry_type,
                    event_code=e.event_code,
                    message=e.message,
                    actor=e.actor,
                    context=e.context,
                    created_at=e.created_at,
                )
                for e in entries
            ],
        )
