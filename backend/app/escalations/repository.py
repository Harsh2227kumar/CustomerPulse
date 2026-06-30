from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.escalations.models import Escalation


class EscalationRepository:
    async def create(
        self,
        db: AsyncSession,
        *,
        complaint_pk: str,
        trigger_type: str,
        reason: str,
        escalated_by: str | None,
        snapshot: dict,
    ) -> Escalation:
        escalation = Escalation(
            complaint_pk=complaint_pk,
            status="open",
            trigger_type=trigger_type,
            reason=reason,
            urgency_score_snapshot=snapshot.get("urgency_score"),
            churn_risk_snapshot=snapshot.get("churn_risk"),
            ai_confidence_snapshot=snapshot.get("ai_confidence"),
            escalated_by=escalated_by,
        )
        db.add(escalation)
        await db.flush()
        return escalation

    async def get(self, db: AsyncSession, escalation_id: str) -> Escalation | None:
        return await db.get(Escalation, escalation_id)

    async def get_open_for_complaint(self, db: AsyncSession, complaint_pk: str) -> Escalation | None:
        stmt = select(Escalation).where(
            Escalation.complaint_pk == complaint_pk,
            Escalation.status == "open"
        )
        return (await db.execute(stmt)).scalar_one_or_none()

    async def list(
        self,
        db: AsyncSession,
        *,
        status: str | None,
        trigger_type: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[Escalation], int]:
        stmt = select(Escalation)
        count_stmt = select(func.count()).select_from(Escalation)

        if status is not None:
            stmt = stmt.where(Escalation.status == status)
            count_stmt = count_stmt.where(Escalation.status == status)
        
        if trigger_type is not None:
            stmt = stmt.where(Escalation.trigger_type == trigger_type)
            count_stmt = count_stmt.where(Escalation.trigger_type == trigger_type)
        
        total = (await db.execute(count_stmt)).scalar_one()
        
        stmt = stmt.order_by(Escalation.created_at.desc()).limit(limit).offset(offset)
        items = (await db.execute(stmt)).scalars().all()
        
        return list(items), total

    async def count_by_status(self, db: AsyncSession) -> dict[str, int]:
        stmt = select(Escalation.status, func.count()).group_by(Escalation.status)
        rows = (await db.execute(stmt)).all()
        return {status: count for status, count in rows}

    async def resolve(
        self,
        db: AsyncSession,
        escalation: Escalation,
        *,
        resolved_by: str,
        resolution_notes: str,
    ) -> Escalation:
        escalation.status = "resolved"
        escalation.resolved_by = resolved_by
        escalation.resolution_notes = resolution_notes
        escalation.resolved_at = func.now()
        await db.flush()
        return escalation
