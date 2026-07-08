from pydantic import BaseModel, Field, field_validator

from app.core.constants import ChurnRisk, Sentiment


class DecisionSource(BaseModel):
    provider: str = Field(min_length=1, max_length=64)
    model: str | None = Field(default=None, max_length=128)
    version: str | None = Field(default=None, max_length=64)
    mode: str = Field(default="deterministic", max_length=64)


class EvidenceSnippet(BaseModel):
    text: str = Field(min_length=1, max_length=500)
    reason_code: str | None = Field(default=None, max_length=128)
    matched_phrase: str | None = Field(default=None, max_length=128)
    source: str = Field(default="narrative", max_length=64)
    start_char: int | None = Field(default=None, ge=0)
    end_char: int | None = Field(default=None, ge=0)

    @field_validator("text", "reason_code", "matched_phrase", "source")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return value.strip()


class SimilarCaseEvidence(BaseModel):
    complaint_id: str
    similarity_score: float = Field(ge=0, le=1)
    category: str | None = None
    product: str | None = None
    issue: str | None = None
    reason_codes: list[str] = Field(default_factory=list)
    next_action: str | None = None
    approved_response: str | None = None
    ai_status: str


class ConfidenceScores(BaseModel):
    sentiment: int = Field(ge=0, le=100)
    category: int = Field(ge=0, le=100)
    urgency: int = Field(ge=0, le=100)
    churn_risk: int | None = Field(default=None, ge=0, le=100)
    draft_response: int | None = Field(default=None, ge=0, le=100)


class KeyIssueResult(BaseModel):
    summary: str = Field(min_length=1, max_length=500)
    evidence_snippets: list[EvidenceSnippet] = Field(default_factory=list)
    reason_codes: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    source: DecisionSource


class RiskSignalResult(BaseModel):
    score: int = Field(ge=0, le=100)
    level: str = Field(min_length=1, max_length=32)
    reason_codes: list[str] = Field(default_factory=list)
    evidence_snippets: list[EvidenceSnippet] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    recommended_action: str | None = Field(default=None, max_length=255)
    source: DecisionSource
    fraud_risk_score: int | None = Field(default=None, ge=0, le=100)
    escalation_risk_score: int | None = Field(default=None, ge=0, le=100)
    hard_blockers: list[str] = Field(default_factory=list)


class ResolutionValidationResult(BaseModel):
    status: str = Field(min_length=1, max_length=32)
    reason_codes: list[str] = Field(default_factory=list)
    evidence_snippets: list[EvidenceSnippet] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    source: DecisionSource
    similarity_score: float | None = Field(default=None, ge=0, le=1)
    reason_code_overlap: float | None = Field(default=None, ge=0, le=1)
    evidence_strength: float | None = Field(default=None, ge=0, le=1)
    category_match: bool | None = None
    product_match: bool | None = None
    issue_match: bool | None = None
    product_family_match: bool | None = None
    issue_family_match: bool | None = None
    hard_blockers: list[str] = Field(default_factory=list)
    recommendation: str | None = Field(default=None, max_length=500)
    notes: str | None = Field(default=None, max_length=500)


class ResolutionRecommendationResult(BaseModel):
    recommendation_type: str = Field(min_length=1, max_length=64)
    recommendation: str = Field(min_length=1, max_length=500)
    reason_codes: list[str] = Field(default_factory=list)
    evidence_snippets: list[EvidenceSnippet] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    source: DecisionSource


class DecisionMetadata(BaseModel):
    decision_type: str = Field(min_length=1, max_length=64)
    confidence: float = Field(ge=0, le=1)
    reason_codes: list[str] = Field(default_factory=list)
    evidence_snippets: list[EvidenceSnippet] = Field(default_factory=list)
    source: DecisionSource
    notes: str | None = Field(default=None, max_length=500)


class AIEnrichment(BaseModel):
    sentiment: Sentiment
    category: str = Field(min_length=1, max_length=255)
    urgency_score: int = Field(ge=0, le=100)
    churn_risk: ChurnRisk
    draft_response: str = ""
    next_action: str = ""
    similar_cases: list[SimilarCaseEvidence] = Field(default_factory=list)
    confidence_scores: ConfidenceScores
    ai_confidence: float = Field(ge=0, le=1)
    ai_reasoning: str | None = None
    reason_codes: list[str] = Field(default_factory=list)
    evidence_snippets: list[EvidenceSnippet] = Field(default_factory=list)
    key_issue: KeyIssueResult | None = None
    risk_signals: RiskSignalResult | None = None
    resolution_validation: ResolutionValidationResult | None = None
    resolution_recommendation: ResolutionRecommendationResult | None = None
    decision_metadata: list[DecisionMetadata] = Field(default_factory=list)
    source_metadata: DecisionSource | None = None

    @field_validator("category", "draft_response", "next_action", "ai_reasoning")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return value.strip()


class ProcessedComplaintResponse(AIEnrichment):
    complaint_id: str
    narrative: str
    channel: str | None = None
    processed_at: str
    ai_status: str
    human_review_reason: str | None = None
    human_review_created_at: str | None = None
