"""
360-degree complaint view endpoint.

Assembles a read-only snapshot from existing modules without modifying any of them.
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.communications.schemas import TimelineResponse
from app.communications.service import CommunicationComplaintNotFoundError, CommunicationService
from app.core.constants import Role
from app.core.security import require_roles
from app.db.session import get_db_session
from app.duplicates.models import DuplicateGroup, DuplicateMember
from app.escalations.repository import EscalationRepository
from app.schemas.complaint import ComplaintDetail
from app.services.complaint_service import ComplaintService

workspace_router = APIRouter(tags=["communications"])


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class DuplicateGroupSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    group_id: str
    status: str
    member_count: int


class EscalationSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    status: str
    trigger_type: str
    reason: str
    escalated_at: datetime


class Complaint360Response(BaseModel):
    model_config = ConfigDict(extra="forbid")

    complaint: ComplaintDetail
    timeline: TimelineResponse
    duplicate_group: Optional[DuplicateGroupSummary] = None
    escalation: Optional[EscalationSummary] = None


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------


@workspace_router.get("/{complaint_id}/360", response_model=Complaint360Response)
async def get_complaint_360(
    complaint_id: str,
    _principal=Depends(require_roles(Role.AGENT, Role.MANAGER, Role.ADMIN)),
    db: AsyncSession = Depends(get_db_session),
) -> Complaint360Response:
    # ── 1. Core complaint detail ──────────────────────────────────────────
    complaint = await ComplaintService().get_detail(db, complaint_id)
    if complaint is None:
        raise HTTPException(status_code=404, detail="Complaint not found")

    # ── 2. Communication timeline ─────────────────────────────────────────
    try:
        timeline = await CommunicationService().get_timeline(db, complaint_id)
    except CommunicationComplaintNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Complaint not found") from exc

    # ── 3. Duplicate-group membership (read-only, no new repo method) ─────
    # Resolve the canonical PK from the complaint detail (source_complaint_id
    # or id — ComplaintService already joins on both, so we can use the pk
    # stored in the DB by fetching the row id via the same or_ logic).
    from sqlalchemy import or_
    from app.models.complaint import Complaint as ComplaintModel

    complaint_pk_row = (
        await db.execute(
            select(ComplaintModel.id).where(
                or_(
                    ComplaintModel.source_complaint_id == complaint_id,
                    ComplaintModel.id == complaint_id,
                )
            )
        )
    ).scalar_one_or_none()

    duplicate_group_summary: Optional[DuplicateGroupSummary] = None
    if complaint_pk_row is not None:
        member = (
            await db.execute(
                select(DuplicateMember).where(
                    DuplicateMember.complaint_pk == complaint_pk_row
                )
            )
        ).scalar_one_or_none()

        if member is not None:
            group = (
                await db.execute(
                    select(DuplicateGroup).where(DuplicateGroup.id == member.group_id)
                )
            ).scalar_one_or_none()

            if group is not None:
                member_count = (
                    await db.execute(
                        select(func.count()).select_from(DuplicateMember).where(
                            DuplicateMember.group_id == group.id
                        )
                    )
                ).scalar_one()

                duplicate_group_summary = DuplicateGroupSummary(
                    group_id=group.id,
                    status=group.status,
                    member_count=member_count,
                )

    # ── 4. Escalation ─────────────────────────────────────────────────────
    escalation_summary: Optional[EscalationSummary] = None
    if complaint_pk_row is not None:
        open_escalation = await EscalationRepository().get_open_for_complaint(
            db, complaint_pk_row
        )
        if open_escalation is not None:
            escalation_summary = EscalationSummary(
                id=open_escalation.id,
                status=open_escalation.status,
                trigger_type=open_escalation.trigger_type,
                reason=open_escalation.reason,
                escalated_at=open_escalation.escalated_at,
            )

    return Complaint360Response(
        complaint=complaint,
        timeline=timeline,
        duplicate_group=duplicate_group_summary,
        escalation=escalation_summary,
    )
