from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


COMPLIANCE_ENGINE_VERSION = "1.0.0"
COMPLIANCE_RULE_SET_VERSION = "1.0.0"


class ComplianceRiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RequiredActionType(StrEnum):
    ACKNOWLEDGE = "acknowledge"
    ESCALATE = "escalate"
    NOTIFY_REGULATOR = "notify_regulator"
    CLOSE_WITH_EVIDENCE = "close_with_evidence"
    PROACTIVE_REVIEW = "proactive_review"


class ComplianceOwner(StrEnum):
    AGENT = "agent"
    MANAGER = "manager"
    COMPLIANCE_OFFICER = "compliance_officer"


class ComplianceBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=True)


class AISignals(ComplianceBaseModel):
    severity: str | None = Field(default=None, max_length=64)
    urgency_score: int | None = Field(default=None, ge=0, le=100)
    fraud_risk_score: int | None = Field(default=None, ge=0, le=100)
    key_issue: str | None = Field(default=None, max_length=255)
    confidence: float | None = Field(default=None, ge=0, le=1)

    @field_validator("severity", "key_issue")
    @classmethod
    def clean_optional_strings(cls, value: str | None) -> str | None:
        if value is None:
            return value
        cleaned = value.strip()
        return cleaned or None



class AIResponseFields(ComplianceBaseModel):
    category: str | None = Field(default=None, max_length=255)
    urgency_score: int | None = Field(default=None, ge=0, le=100)
    draft_response: str | None = Field(default=None, max_length=10000)
    resolution: str | None = Field(default=None, max_length=2000)
    next_action: str | None = Field(default=None, max_length=2000)
    ai_confidence: float | None = Field(default=None, ge=0, le=1)

    @field_validator("category", "draft_response", "resolution", "next_action")
    @classmethod
    def clean_optional_strings(cls, value: str | None) -> str | None:
        if value is None:
            return value
        cleaned = value.strip()
        return cleaned or None

class SLAState(ComplianceBaseModel):
    is_breached: bool = False
    breach_risk_level: str | None = Field(default=None, max_length=32)
    days_elapsed: int | None = Field(default=None, ge=0)
    days_to_deadline: int | None = None

    @field_validator("breach_risk_level")
    @classmethod
    def clean_breach_risk(cls, value: str | None) -> str | None:
        if value is None:
            return value
        cleaned = value.strip().lower()
        return cleaned or None


class ComplaintComplianceInput(ComplianceBaseModel):
    complaint_id: str = Field(min_length=1, max_length=128)
    source_complaint_id: str | None = Field(default=None, max_length=128)
    product: str | None = Field(default=None, max_length=255)
    issue: str | None = Field(default=None, max_length=255)
    sub_issue: str | None = Field(default=None, max_length=255)
    narrative: str | None = Field(default=None, max_length=10000)
    channel: str | None = Field(default=None, max_length=64)
    date_received: datetime
    acknowledged_at: datetime | None = None
    resolved_at: datetime | None = None
    amount_disputed: float | None = Field(default=None, ge=0)
    kyc_status: str | None = Field(default=None, max_length=64)
    kyc_update_overdue: bool = False
    kyc_missing_fields: list[str] = Field(default_factory=list)
    customer_notified_at: datetime | None = None
    customer_service_breached: bool = False
    missing_documents: list[str] = Field(default_factory=list)
    is_incomplete: bool = False
    missing_investigation_evidence: bool = False
    ai_signals: AISignals = Field(default_factory=AISignals)
    response_fields: AIResponseFields = Field(default_factory=AIResponseFields)
    sla: SLAState = Field(default_factory=SLAState)

    @field_validator("product", "issue", "sub_issue", "narrative", "channel", "source_complaint_id", "kyc_status")
    @classmethod
    def clean_optional_strings(cls, value: str | None) -> str | None:
        if value is None:
            return value
        cleaned = value.strip()
        return cleaned or None

    @field_validator("kyc_missing_fields", "missing_documents")
    @classmethod
    def clean_string_lists(cls, value: list[str]) -> list[str]:
        return [item.strip() for item in value if item.strip()]

    @model_validator(mode="after")
    def validate_event_order(self) -> "ComplaintComplianceInput":
        if self.acknowledged_at and self.acknowledged_at < self.date_received:
            raise ValueError("acknowledged_at must be on or after date_received")
        if self.resolved_at and self.resolved_at < self.date_received:
            raise ValueError("resolved_at must be on or after date_received")
        if self.customer_notified_at and self.customer_notified_at < self.date_received:
            raise ValueError("customer_notified_at must be on or after date_received")
        return self


class RuleAction(ComplianceBaseModel):
    action_type: RequiredActionType
    owner: ComplianceOwner
    description: str = Field(min_length=1, max_length=500)
    deadline_days: int = Field(ge=0)


class ComplianceRule(ComplianceBaseModel):
    rule_id: str = Field(min_length=1, max_length=64)
    description: str = Field(min_length=1, max_length=500)
    condition_type: str = Field(min_length=1, max_length=64)
    severity: ComplianceRiskLevel
    mandatory_action: bool = False
    action: RuleAction


class RequiredAction(ComplianceBaseModel):
    action_type: RequiredActionType
    owner: ComplianceOwner
    description: str
    deadline_at: datetime


class TriggeredRule(ComplianceBaseModel):
    rule_id: str
    description: str
    severity: ComplianceRiskLevel
    mandatory_action: bool
    evidence: list[str] = Field(min_length=1)
    triggered_at: datetime
    required_action: RequiredAction


class SLAComplianceReading(ComplianceBaseModel):
    is_breached: bool
    breach_risk_level: str | None = None
    regulatory_interpretation: str
    proactive_flag: bool = False


class ComplianceResult(ComplianceBaseModel):
    complaint_id: str
    source_complaint_id: str | None = None
    compliance_risk_level: ComplianceRiskLevel
    triggered_rules: list[TriggeredRule]
    required_actions: list[RequiredAction]
    reason_codes: list[str]
    sla_reading: SLAComplianceReading
    evaluated_at: datetime
    engine_version: str = Field(default=COMPLIANCE_ENGINE_VERSION)
    rule_set_version: str = Field(default=COMPLIANCE_RULE_SET_VERSION)


class ComplianceEvidenceStoreRequest(ComplianceBaseModel):
    result: ComplianceResult
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("notes")
    @classmethod
    def clean_notes(cls, value: str | None) -> str | None:
        if value is None:
            return value
        cleaned = value.strip()
        return cleaned or None


class ComplianceEvidenceRead(ComplianceBaseModel):
    id: str
    complaint_id: str
    source_complaint_id: str | None = None
    risk_level: ComplianceRiskLevel
    required_action: RequiredActionType | None = None
    regulatory_flag: bool
    regulatory_interpretation: str
    triggered_rules: list[dict]
    evidence_snippets: list[str]
    required_actions: list[dict]
    reason_codes: list[str]
    result: ComplianceResult
    notes: str | None = None
    evaluated_at: datetime
    created_at: datetime
    updated_at: datetime


class ComplianceEvidenceListResponse(ComplianceBaseModel):
    items: list[ComplianceEvidenceRead]
    limit: int
    offset: int
    count: int


class ComplianceRegulator(StrEnum):
    RBI = "RBI"
    NPCI = "NPCI"
    SEBI = "SEBI"
    IRDAI = "IRDAI"
    BANK_INTERNAL = "BANK_INTERNAL"


class RegulatoryDocumentType(StrEnum):
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"
    MARKDOWN = "markdown"
    HTML = "html"


class RegulatoryDocumentStatus(StrEnum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    INDEXED = "indexed"
    REVIEW_REQUIRED = "review_required"
    ACTIVE = "active"
    ARCHIVED = "archived"
    FAILED = "failed"


class ComplianceRuleStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    INACTIVE = "inactive"
    RETIRED = "retired"


class ReasonCodeStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    RETIRED = "retired"


class ComplianceRuleDefinitionBase(ComplianceBaseModel):
    rule_id: str = Field(min_length=1, max_length=128)
    rule_name: str = Field(min_length=1, max_length=255)
    regulator: ComplianceRegulator
    domain: str = Field(min_length=1, max_length=128)
    version: str = Field(min_length=1, max_length=32)
    status: ComplianceRuleStatus = ComplianceRuleStatus.DRAFT
    description: str = Field(min_length=1, max_length=2000)
    evaluation_type: str = Field(min_length=1, max_length=64)
    severity: ComplianceRiskLevel = ComplianceRiskLevel.MEDIUM
    reason_code: str | None = Field(default=None, max_length=64)
    effective_from: datetime
    effective_to: datetime | None = None

    @field_validator("rule_id", "rule_name", "domain", "version", "description", "evaluation_type", "reason_code")
    @classmethod
    def clean_rule_strings(cls, value: str | None) -> str | None:
        if value is None:
            return value
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("value must not be blank")
        return cleaned

    @field_validator("rule_id", "reason_code")
    @classmethod
    def normalize_codes(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return value.strip().upper().replace(" ", "_")

    @field_validator("domain", "evaluation_type")
    @classmethod
    def normalize_classifier_fields(cls, value: str) -> str:
        return value.strip().lower().replace(" ", "_")

    @model_validator(mode="after")
    def validate_effective_window(self) -> "ComplianceRuleDefinitionBase":
        if self.effective_to and self.effective_to < self.effective_from:
            raise ValueError("effective_to must be on or after effective_from")
        return self


class ComplianceRuleDefinitionCreate(ComplianceRuleDefinitionBase):
    pass


class ComplianceRuleDefinitionUpdate(ComplianceRuleDefinitionBase):
    pass


class ComplianceRuleDefinitionRead(ComplianceRuleDefinitionBase):
    id: str
    supersedes_rule_record_id: str | None = None
    created_at: datetime
    updated_at: datetime


class ComplianceRuleDefinitionListResponse(ComplianceBaseModel):
    items: list[ComplianceRuleDefinitionRead]
    limit: int
    offset: int
    count: int


class ReasonCodeBase(ComplianceBaseModel):
    code: str = Field(min_length=1, max_length=64)
    description: str = Field(min_length=1, max_length=2000)
    severity: ComplianceRiskLevel
    status: ReasonCodeStatus = ReasonCodeStatus.ACTIVE

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        cleaned = value.strip().upper().replace(" ", "_")
        if not cleaned:
            raise ValueError("value must not be blank")
        return cleaned

    @field_validator("description")
    @classmethod
    def clean_description(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("value must not be blank")
        return cleaned


class ReasonCodeCreate(ReasonCodeBase):
    pass


class ReasonCodeRead(ReasonCodeBase):
    id: str
    created_at: datetime
    updated_at: datetime


class ReasonCodeListResponse(ComplianceBaseModel):
    items: list[ReasonCodeRead]
    limit: int
    offset: int
    count: int


class RegulatoryDocumentBase(ComplianceBaseModel):
    regulator: ComplianceRegulator
    document_title: str = Field(min_length=1, max_length=255)
    document_type: RegulatoryDocumentType
    source_filename: str = Field(min_length=1, max_length=255)
    source_url: str | None = Field(default=None, max_length=1000)
    storage_path: str = Field(min_length=1, max_length=1000)
    version: str = Field(min_length=1, max_length=64)
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    status: RegulatoryDocumentStatus = RegulatoryDocumentStatus.UPLOADED
    uploaded_by: str | None = Field(default=None, max_length=128)

    @field_validator("document_title", "source_filename", "source_url", "storage_path", "version", "uploaded_by")
    @classmethod
    def clean_document_strings(cls, value: str | None) -> str | None:
        if value is None:
            return value
        cleaned = value.strip()
        if not cleaned:
            return None
        return cleaned

    @field_validator("version")
    @classmethod
    def require_document_version(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("version must not be blank")
        return value

    @model_validator(mode="after")
    def validate_effective_window(self) -> "RegulatoryDocumentBase":
        if self.effective_to and self.effective_from and self.effective_to < self.effective_from:
            raise ValueError("effective_to must be on or after effective_from")
        return self


class RegulatoryDocumentCreate(RegulatoryDocumentBase):
    status: RegulatoryDocumentStatus = RegulatoryDocumentStatus.UPLOADED


class RegulatoryDocumentRead(RegulatoryDocumentBase):
    id: str
    uploaded_at: datetime
    created_at: datetime
    updated_at: datetime


class RegulatoryDocumentListResponse(ComplianceBaseModel):
    items: list[RegulatoryDocumentRead]
    limit: int
    offset: int
    count: int


class RegulatoryDocumentPageRead(ComplianceBaseModel):
    id: str
    document_id: str
    page_number: int
    raw_text: str
    cleaned_text: str
    markdown_text: str
    extraction_status: str
    created_at: datetime


class RegulatoryDocumentMarkdownFileRead(ComplianceBaseModel):
    id: str
    document_id: str
    markdown_path: str
    conversion_tool: str
    conversion_status: str
    conversion_warnings: list[str]
    created_at: datetime
    updated_at: datetime


class RegulatoryKnowledgeChunkRead(ComplianceBaseModel):
    id: str
    document_id: str
    chunk_index: int
    regulator: ComplianceRegulator
    domain: str
    section_reference: str | None = None
    page_start: int | None = None
    page_end: int | None = None
    chunk_text: str
    summary: str | None = None
    keywords: list[str]
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    status: str
    embedding_model: str | None = None
    created_at: datetime
    updated_at: datetime


class RegulatoryDocumentProcessResult(ComplianceBaseModel):
    document: RegulatoryDocumentRead
    markdown_file: RegulatoryDocumentMarkdownFileRead | None = None
    pages_created: int = Field(ge=0)
    chunks_created: int = Field(ge=0)
    warnings: list[str] = Field(default_factory=list)


class RegulatoryChunkEmbeddingBackfillResult(ComplianceBaseModel):
    document_id: str | None = None
    embedding_model: str
    embedded_count: int = Field(ge=0)
    skipped_count: int = Field(ge=0)


class RegulatoryKnowledgeSearchRequest(ComplianceBaseModel):
    query: str = Field(min_length=1, max_length=2000)
    regulator: ComplianceRegulator | None = None
    domain: str | None = Field(default=None, max_length=128)
    status: str | None = Field(default=None, max_length=32)
    effective_on: datetime | None = None
    limit: int = Field(default=5, ge=1, le=20)
    min_similarity: float = Field(default=0.0, ge=0, le=1)

    @field_validator("query", "domain", "status")
    @classmethod
    def clean_search_strings(cls, value: str | None) -> str | None:
        if value is None:
            return value
        cleaned = value.strip()
        return cleaned or None

    @field_validator("domain")
    @classmethod
    def normalize_search_domain(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return value.strip().lower().replace(" ", "_")


class RegulatoryKnowledgeSearchResult(ComplianceBaseModel):
    chunk_id: str
    document_id: str
    document_title: str | None = None
    regulator: ComplianceRegulator
    domain: str
    section_reference: str | None = None
    page_start: int | None = None
    page_end: int | None = None
    similarity_score: float = Field(ge=0, le=1)
    chunk_text: str
    keywords: list[str] = Field(default_factory=list)
    effective_from: datetime | None = None
    effective_to: datetime | None = None


class RegulatoryKnowledgeSearchResponse(ComplianceBaseModel):
    query: str
    embedding_model: str
    results: list[RegulatoryKnowledgeSearchResult]
