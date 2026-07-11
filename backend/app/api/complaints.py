from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import ValidationError
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import ChurnRisk, ProcessingStatus, ReviewReason, Role, Sentiment
from app.core.config import Settings, get_settings
from app.core.security import Principal, require_roles
from app.db.session import get_db_session
from app.compliance.explainability.service import generate_explanation_with_sources
from app.compliance.service import ComplianceEvidenceService
from app.models.complaint import Complaint
from app.schemas.complaint import ComplaintAssignRequest, ComplaintComplianceExplanationResponse, ComplaintDetail, ComplaintFilters, ComplaintListResponse
from app.services.complaint_service import ComplaintService

router = APIRouter(prefix="/api", tags=["complaints"])


@router.get("/complaints", response_model=ComplaintListResponse)
async def list_complaints(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    sentiment: Sentiment | None = None,
    channel: str | None = None,
    product: str | None = None,
    sub_product: str | None = None,
    sub_issue: str | None = None,
    company: str | None = None,
    category: str | None = None,
    churn_risk: ChurnRisk | None = None,
    urgency_min: int | None = Query(default=None, ge=0, le=100),
    urgency_max: int | None = Query(default=None, ge=0, le=100),
    date_received_min: datetime | None = None,
    date_received_max: datetime | None = None,
    timely_response: bool | None = None,
    ai_status: ProcessingStatus | None = None,
    human_review_reason: ReviewReason | None = None,
    search: str | None = Query(default=None, max_length=256),
    sort_by: Literal[
        "created_at",
        "date_received",
        "processed_at",
        "urgency_score",
        "sentiment",
        "churn_risk",
        "ai_confidence",
        "ai_status",
        "relevance",
    ] = "created_at",
    sort_direction: Literal["asc", "desc"] = "desc",
    db: AsyncSession = Depends(get_db_session),
) -> ComplaintListResponse:
    try:
        filters = ComplaintFilters(
            limit=limit,
            offset=offset,
            sentiment=sentiment,
            channel=channel,
            product=product,
            sub_product=sub_product,
            sub_issue=sub_issue,
            company=company,
            category=category,
            churn_risk=churn_risk,
            urgency_min=urgency_min,
            urgency_max=urgency_max,
            date_received_min=date_received_min,
            date_received_max=date_received_max,
            timely_response=timely_response,
            ai_status=ai_status,
            human_review_reason=human_review_reason,
            search=search,
            sort_by=sort_by,
            sort_direction=sort_direction,
        )
    except ValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail="Invalid complaint filter or sorting combination.",
        ) from exc
    return await ComplaintService().list_complaints(db, filters)


@router.get("/complaints/categories", response_model=list[str])
async def get_complaint_categories() -> list[str]:
    from app.ai.ml_models.classifier import STANDARD_CATEGORIES
    return STANDARD_CATEGORIES



@router.get("/complaints/{complaint_id}/compliance-explanation", response_model=ComplaintComplianceExplanationResponse)
async def get_complaint_compliance_explanation(
    complaint_id: str,
    limit: int = Query(default=5, ge=1, le=20),
    db: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> ComplaintComplianceExplanationResponse:
    complaint = (
        await db.execute(
            select(Complaint).where(
                or_(Complaint.source_complaint_id == complaint_id, Complaint.id == complaint_id)
            )
        )
    ).scalar_one_or_none()
    if complaint is None:
        raise HTTPException(status_code=404, detail="Complaint not found.")

    evidence_service = ComplianceEvidenceService()
    records, count = await evidence_service.list_records(
        db,
        limit=1,
        offset=0,
        complaint_id=complaint.id,
    )
    if not count and complaint.source_complaint_id:
        records, count = await evidence_service.list_records(
            db,
            limit=1,
            offset=0,
            complaint_id=complaint.source_complaint_id,
        )

    if not count or not records:
        return ComplaintComplianceExplanationResponse(
            available=False,
            message="No stored compliance evidence exists for this complaint yet. Process or re-run the complaint to trigger compliance evaluation.",
            complaint_id=complaint.source_complaint_id or complaint.id,
        )

    evidence_record = records[0]
    complaint_payload = {
        key: value
        for key, value in complaint.__dict__.items()
        if not key.startswith("_")
    }
    explanation = await generate_explanation_with_sources(
        db,
        evidence_record.result.model_dump(mode="json"),
        complaint_payload,
        settings=settings,
        limit=limit,
    )
    return ComplaintComplianceExplanationResponse(
        available=True,
        message="Compliance evidence and regulatory source citations are available for this complaint.",
        complaint_id=complaint.source_complaint_id or complaint.id,
        evidence_record_id=evidence_record.id,
        risk_level=evidence_record.risk_level,
        regulatory_flag=evidence_record.regulatory_flag,
        required_action=evidence_record.required_action,
        evaluated_at=evidence_record.evaluated_at,
        explanation_with_sources=explanation,
    )

@router.get("/complaints/{complaint_id}", response_model=ComplaintDetail)
async def get_complaint_detail(
    complaint_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> ComplaintDetail:
    detail = await ComplaintService().get_detail(db, complaint_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Complaint not found.")
    return detail


@router.post("/complaints/{complaint_id}/assign", response_model=ComplaintDetail)
async def assign_complaint(
    complaint_id: str,
    request: ComplaintAssignRequest,
    db: AsyncSession = Depends(get_db_session),
    principal: Principal = Depends(require_roles(Role.MANAGER, Role.ADMIN)),
) -> ComplaintDetail:
    detail = await ComplaintService().assign_agent(db, complaint_id, request.agent_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Complaint not found.")
    return detail
