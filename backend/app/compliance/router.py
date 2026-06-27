from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.compliance.engine import ComplianceEngine
from app.compliance.explainability.models import ComplianceExplanation
from app.compliance.explainability.service import generate_explanation
from app.compliance.models import (
    ComplaintComplianceInput,
    ComplianceEvidenceListResponse,
    ComplianceEvidenceRead,
    ComplianceEvidenceStoreRequest,
    ComplianceRegulator,
    ComplianceResult,
    ComplianceRiskLevel,
    ComplianceRuleDefinitionCreate,
    ComplianceRuleDefinitionListResponse,
    ComplianceRuleDefinitionRead,
    ComplianceRuleDefinitionUpdate,
    ComplianceRuleStatus,
    ReasonCodeCreate,
    ReasonCodeListResponse,
    ReasonCodeRead,
    ReasonCodeStatus,
)
from app.compliance.service import (
    ComplianceEvidenceNotFoundError,
    ComplianceEvidenceService,
    ComplianceKnowledgeBaseService,
    ComplianceRuleNotFoundError,
    ComplianceRuleVersionConflictError,
    ReasonCodeConflictError,
)
from app.db.session import get_db_session
from app.models.complaint import Complaint


router = APIRouter(prefix="/api/compliance", tags=["compliance"])


@router.post("/evaluate", response_model=ComplianceResult)
async def evaluate_compliance(
    payload: ComplaintComplianceInput,
    store: bool = Query(default=True),
    db: AsyncSession = Depends(get_db_session),
) -> ComplianceResult:
    result = ComplianceEngine().evaluate(payload)
    if store:
        await ComplianceEvidenceService().store_result(db, result)
    return result


@router.post("/evidence", response_model=ComplianceEvidenceRead, status_code=201)
async def store_compliance_evidence(
    payload: ComplianceEvidenceStoreRequest,
    db: AsyncSession = Depends(get_db_session),
) -> ComplianceEvidenceRead:
    return await ComplianceEvidenceService().store_request(db, payload)


@router.get("/evidence", response_model=ComplianceEvidenceListResponse)
async def list_compliance_evidence(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    complaint_id: str | None = Query(default=None),
    risk_level: ComplianceRiskLevel | None = Query(default=None),
    regulatory_flag: bool | None = Query(default=None),
    product: str | None = Query(default=None),
    company: str | None = Query(default=None),
    channel: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db_session),
) -> ComplianceEvidenceListResponse:
    items, count = await ComplianceEvidenceService().list_records(
        db,
        limit=limit,
        offset=offset,
        complaint_id=complaint_id,
        risk_level=risk_level,
        regulatory_flag=regulatory_flag,
        product=product,
        company=company,
        channel=channel,
    )
    return ComplianceEvidenceListResponse(items=items, limit=limit, offset=offset, count=count)


@router.get("/evidence/{record_id}", response_model=ComplianceEvidenceRead)
async def get_compliance_evidence(
    record_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> ComplianceEvidenceRead:
    try:
        return await ComplianceEvidenceService().get_record(db, record_id)
    except ComplianceEvidenceNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Compliance evidence record not found.") from exc


def _complaint_record_to_dict(complaint: Complaint) -> dict:
    return {
        key: value
        for key, value in complaint.__dict__.items()
        if not key.startswith("_")
    }


@router.get("/evidence/{record_id}/explain", response_model=ComplianceExplanation)
async def get_compliance_explanation(
    record_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> ComplianceExplanation:
    try:
        evidence_record = await ComplianceEvidenceService().get_record(db, record_id)
    except ComplianceEvidenceNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Compliance evidence record not found.") from exc

    complaint_record = await db.get(Complaint, evidence_record.complaint_id)
    if complaint_record is None:
        raise HTTPException(status_code=404, detail="Complaint associated with evidence not found.")

    return generate_explanation(
        evidence_record.result.model_dump(mode="json"),
        _complaint_record_to_dict(complaint_record),
    )


@router.post("/explain", response_model=ComplianceExplanation)
async def explain_compliance(
    payload: ComplaintComplianceInput,
    db: AsyncSession = Depends(get_db_session),
) -> ComplianceExplanation:
    result = ComplianceEngine().evaluate(payload)
    return generate_explanation(
        result.model_dump(mode="json"),
        payload.model_dump(mode="json"),
    )


@router.delete("/evidence/{record_id}", status_code=204)
async def delete_compliance_evidence(
    record_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> None:
    try:
        await ComplianceEvidenceService().delete_record(db, record_id)
    except ComplianceEvidenceNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Compliance evidence record not found.") from exc


@router.get("/rules", response_model=ComplianceRuleDefinitionListResponse)
async def list_compliance_rules(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    regulator: ComplianceRegulator | None = Query(default=None),
    domain: str | None = Query(default=None),
    status: ComplianceRuleStatus | None = Query(default=None),
    active_on: datetime | None = Query(default=None),
    db: AsyncSession = Depends(get_db_session),
) -> ComplianceRuleDefinitionListResponse:
    return await ComplianceKnowledgeBaseService().list_rules(
        db,
        limit=limit,
        offset=offset,
        regulator=regulator,
        domain=domain.strip().lower().replace(" ", "_") if domain else None,
        status=status,
        active_on=active_on,
    )


@router.get("/rules/{record_id}", response_model=ComplianceRuleDefinitionRead)
async def get_compliance_rule(
    record_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> ComplianceRuleDefinitionRead:
    try:
        return await ComplianceKnowledgeBaseService().get_rule(db, record_id)
    except ComplianceRuleNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Compliance rule not found.") from exc


@router.post("/rules", response_model=ComplianceRuleDefinitionRead, status_code=201)
async def create_compliance_rule(
    payload: ComplianceRuleDefinitionCreate,
    db: AsyncSession = Depends(get_db_session),
) -> ComplianceRuleDefinitionRead:
    try:
        return await ComplianceKnowledgeBaseService().create_rule(db, payload)
    except ComplianceRuleVersionConflictError as exc:
        raise HTTPException(status_code=409, detail="Compliance rule version already exists.") from exc


@router.put("/rules/{record_id}", response_model=ComplianceRuleDefinitionRead)
async def update_compliance_rule(
    record_id: str,
    payload: ComplianceRuleDefinitionUpdate,
    db: AsyncSession = Depends(get_db_session),
) -> ComplianceRuleDefinitionRead:
    try:
        return await ComplianceKnowledgeBaseService().update_rule_version(db, record_id, payload)
    except ComplianceRuleNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Compliance rule not found.") from exc
    except ComplianceRuleVersionConflictError as exc:
        raise HTTPException(status_code=409, detail="Compliance rule version already exists.") from exc


@router.get("/reason-codes", response_model=ReasonCodeListResponse)
async def list_reason_codes(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    status: ReasonCodeStatus | None = Query(default=None),
    db: AsyncSession = Depends(get_db_session),
) -> ReasonCodeListResponse:
    return await ComplianceKnowledgeBaseService().list_reason_codes(db, limit=limit, offset=offset, status=status)


@router.post("/reason-codes", response_model=ReasonCodeRead, status_code=201)
async def create_reason_code(
    payload: ReasonCodeCreate,
    db: AsyncSession = Depends(get_db_session),
) -> ReasonCodeRead:
    try:
        return await ComplianceKnowledgeBaseService().create_reason_code(db, payload)
    except ReasonCodeConflictError as exc:
        raise HTTPException(status_code=409, detail="Reason code already exists.") from exc



