from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import Role
from app.core.security import require_roles
from app.db.session import get_db_session
from app.escalations.schemas import (
    EscalationCreateRequest,
    EscalationListQuery,
    EscalationListResponse,
    EscalationRead,
    EscalationResolveRequest,
)
from app.escalations.service import (
    EscalationAlreadyOpenError,
    EscalationComplaintNotFoundError,
    EscalationNotFoundError,
    EscalationService,
)

escalations_router = APIRouter(prefix="/api/escalations", tags=["escalations"])
complaints_escalations_router = APIRouter(prefix="/api/complaints", tags=["escalations"])


@escalations_router.get("", response_model=EscalationListResponse)
async def list_escalations(
    filters: EscalationListQuery = Depends(),
    _principal=Depends(require_roles(Role.MANAGER, Role.ADMIN)),
    db: AsyncSession = Depends(get_db_session),
) -> EscalationListResponse:
    return await EscalationService().list_escalations(db, filters)


@escalations_router.get("/{escalation_id}", response_model=EscalationRead)
async def get_escalation(
    escalation_id: str,
    _principal=Depends(require_roles(Role.MANAGER, Role.ADMIN)),
    db: AsyncSession = Depends(get_db_session),
) -> EscalationRead:
    try:
        return await EscalationService().get_escalation(db, escalation_id)
    except EscalationNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Escalation not found.") from exc


@escalations_router.post("/{escalation_id}/resolve", response_model=EscalationRead)
async def resolve_escalation(
    escalation_id: str,
    payload: EscalationResolveRequest,
    principal=Depends(require_roles(Role.MANAGER, Role.ADMIN)),
    db: AsyncSession = Depends(get_db_session),
) -> EscalationRead:
    try:
        return await EscalationService().resolve(db, escalation_id, payload, actor=principal.actor)
    except EscalationNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Escalation not found.") from exc


@complaints_escalations_router.post("/{complaint_id}/escalate", response_model=EscalationRead)
async def escalate_complaint(
    complaint_id: str,
    payload: EscalationCreateRequest,
    principal=Depends(require_roles(Role.AGENT, Role.MANAGER, Role.ADMIN)),
    db: AsyncSession = Depends(get_db_session),
) -> EscalationRead:
    try:
        return await EscalationService().escalate_manual(db, complaint_id, payload, actor=principal.actor)
    except EscalationComplaintNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Complaint not found.") from exc
    except EscalationAlreadyOpenError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
