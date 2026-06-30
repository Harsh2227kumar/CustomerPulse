from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.compliance.engine import ComplianceEngine
from app.core.config import Settings, get_settings
from app.compliance.explainability.models import ComplianceExplanation, ComplianceExplanationWithSources
from app.compliance.explainability.service import generate_explanation, generate_explanation_with_sources
from app.core.constants import Role
from app.core.security import Principal, require_roles
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
    RegulatoryChunkEmbeddingBackfillResult,
    RegulatoryDocumentCreate,
    RegulatoryDocumentListResponse,
    RegulatoryDocumentProcessResult,
    RegulatoryDocumentRead,
    RegulatoryDocumentStatus,
    RegulatoryDocumentType,
    RegulatoryKnowledgeSearchRequest,
    RegulatoryKnowledgeSearchResponse,
)
from app.compliance.service import (
    ComplianceEvidenceNotFoundError,
    ComplianceEvidenceService,
    ComplianceKnowledgeBaseService,
    ComplianceRuleNotFoundError,
    ComplianceRuleVersionConflictError,
    ReasonCodeConflictError,
    RegulatoryDocumentConflictError,
    RegulatoryDocumentNotFoundError,
    RegulatoryDocumentProcessingError,
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


@router.get("/evidence/{record_id}/explain-with-sources", response_model=ComplianceExplanationWithSources)
async def get_compliance_explanation_with_sources(
    record_id: str,
    limit: int = Query(default=5, ge=1, le=20),
    db: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> ComplianceExplanationWithSources:
    try:
        evidence_record = await ComplianceEvidenceService().get_record(db, record_id)
    except ComplianceEvidenceNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Compliance evidence record not found.") from exc

    complaint_record = await db.get(Complaint, evidence_record.complaint_id)
    if complaint_record is None:
        raise HTTPException(status_code=404, detail="Complaint associated with evidence not found.")

    return await generate_explanation_with_sources(
        db,
        evidence_record.result.model_dump(mode="json"),
        _complaint_record_to_dict(complaint_record),
        settings=settings,
        limit=limit,
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


@router.post("/explain-with-sources", response_model=ComplianceExplanationWithSources)
async def explain_compliance_with_sources(
    payload: ComplaintComplianceInput,
    limit: int = Query(default=5, ge=1, le=20),
    db: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> ComplianceExplanationWithSources:
    result = ComplianceEngine().evaluate(payload)
    return await generate_explanation_with_sources(
        db,
        result.model_dump(mode="json"),
        payload.model_dump(mode="json"),
        settings=settings,
        limit=limit,
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




@router.post("/regulatory-documents/upload", response_model=RegulatoryDocumentRead, status_code=201)
async def upload_regulatory_document(
    file: UploadFile = File(...),
    regulator: ComplianceRegulator = Form(default=ComplianceRegulator.RBI),
    document_title: str = Form(...),
    version: str = Form(...),
    effective_from: datetime | None = Form(default=None),
    effective_to: datetime | None = Form(default=None),
    principal: Principal = Depends(require_roles(Role.ADMIN)),
    db: AsyncSession = Depends(get_db_session),
) -> RegulatoryDocumentRead:
    try:
        return await ComplianceKnowledgeBaseService().create_uploaded_regulatory_document(
            db,
            regulator=regulator.value if hasattr(regulator, "value") else str(regulator),
            document_title=document_title,
            version=version,
            source_filename=file.filename or "regulatory_document",
            file_bytes=await file.read(),
            effective_from=effective_from,
            effective_to=effective_to,
            uploaded_by=principal.actor,
        )
    except RegulatoryDocumentConflictError as exc:
        raise HTTPException(status_code=409, detail="Regulatory document version already exists.") from exc
    except RegulatoryDocumentProcessingError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/regulatory-documents", response_model=RegulatoryDocumentRead, status_code=201)
async def create_regulatory_document(
    payload: RegulatoryDocumentCreate,
    principal: Principal = Depends(require_roles(Role.ADMIN)),
    db: AsyncSession = Depends(get_db_session),
) -> RegulatoryDocumentRead:
    try:
        return await ComplianceKnowledgeBaseService().create_regulatory_document(
            db,
            payload,
            uploaded_by=principal.actor,
        )
    except RegulatoryDocumentConflictError as exc:
        raise HTTPException(status_code=409, detail="Regulatory document version already exists.") from exc


@router.get("/regulatory-documents", response_model=RegulatoryDocumentListResponse)
async def list_regulatory_documents(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    regulator: ComplianceRegulator | None = Query(default=None),
    status: RegulatoryDocumentStatus | None = Query(default=None),
    document_type: RegulatoryDocumentType | None = Query(default=None),
    _principal: Principal = Depends(require_roles(Role.ADMIN)),
    db: AsyncSession = Depends(get_db_session),
) -> RegulatoryDocumentListResponse:
    return await ComplianceKnowledgeBaseService().list_regulatory_documents(
        db,
        limit=limit,
        offset=offset,
        regulator=regulator,
        status=status,
        document_type=document_type,
    )


@router.get("/regulatory-documents/{document_id}", response_model=RegulatoryDocumentRead)
async def get_regulatory_document(
    document_id: str,
    _principal: Principal = Depends(require_roles(Role.ADMIN)),
    db: AsyncSession = Depends(get_db_session),
) -> RegulatoryDocumentRead:
    try:
        return await ComplianceKnowledgeBaseService().get_regulatory_document(db, document_id)
    except RegulatoryDocumentNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Regulatory document not found.") from exc


@router.post("/regulatory-documents/{document_id}/process", response_model=RegulatoryDocumentProcessResult)
async def process_regulatory_document(
    document_id: str,
    _principal: Principal = Depends(require_roles(Role.ADMIN)),
    db: AsyncSession = Depends(get_db_session),
) -> RegulatoryDocumentProcessResult:
    try:
        return await ComplianceKnowledgeBaseService().process_regulatory_document(db, document_id)
    except RegulatoryDocumentNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Regulatory document not found.") from exc
    except RegulatoryDocumentProcessingError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

@router.post("/regulatory-documents/{document_id}/embedding-backfill", response_model=RegulatoryChunkEmbeddingBackfillResult)
async def embed_regulatory_document_chunks(
    document_id: str,
    limit: int = Query(default=100, ge=1, le=500),
    _principal: Principal = Depends(require_roles(Role.ADMIN)),
    db: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> RegulatoryChunkEmbeddingBackfillResult:
    return await ComplianceKnowledgeBaseService().embed_regulatory_chunks(
        db,
        settings=settings,
        document_id=document_id,
        limit=limit,
    )


@router.post("/regulatory-search", response_model=RegulatoryKnowledgeSearchResponse)
async def search_regulatory_knowledge(
    payload: RegulatoryKnowledgeSearchRequest,
    _principal: Principal = Depends(require_roles(Role.ADMIN)),
    db: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> RegulatoryKnowledgeSearchResponse:
    return await ComplianceKnowledgeBaseService().search_regulatory_knowledge(
        db,
        payload,
        settings=settings,
    )
