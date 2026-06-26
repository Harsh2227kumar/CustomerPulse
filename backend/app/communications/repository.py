from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.communications.models import CommunicationHistory


class CommunicationRepository:
    async def create_entry(
        self,
        db: AsyncSession,
        *,
        complaint_pk: str,
        entry_type: str,
        event_code: str | None,
        message: str,
        actor: str | None,
        context: dict | None,
    ) -> CommunicationHistory:
        entry = CommunicationHistory(
            complaint_pk=complaint_pk,
            entry_type=entry_type,
            event_code=event_code,
            message=message,
            actor=actor,
            context=context,
        )
        db.add(entry)
        await db.flush()
        return entry

    async def list_for_complaint(
        self,
        db: AsyncSession,
        complaint_pk: str,
    ) -> Sequence[CommunicationHistory]:
        stmt = (
            select(CommunicationHistory)
            .where(CommunicationHistory.complaint_pk == complaint_pk)
            .order_by(CommunicationHistory.created_at.asc())
        )
        return (await db.execute(stmt)).scalars().all()
