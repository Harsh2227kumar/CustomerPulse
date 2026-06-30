from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ExplainabilityBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RuleExplanation(ExplainabilityBaseModel):
    rule_id: str = Field(min_length=1)
    rule_description: str = Field(min_length=1)
    why_triggered: str = Field(min_length=1)
    complaint_fields_used: list[str]
    evidence_snippets: list[str]
    confidence: Literal["high", "medium", "low"]
    triggered_at: datetime


class RiskJustification(ExplainabilityBaseModel):
    overall_risk_level: Literal["low", "medium", "high", "critical"]
    reason_summary: str = Field(min_length=1)
    contributing_factors: list[str]
    dominant_rule_id: str


class ComplianceExplanation(ExplainabilityBaseModel):
    complaint_id: str = Field(min_length=1)
    evaluated_at: datetime
    rule_explanations: list[RuleExplanation]
    risk_justification: RiskJustification
    audit_metadata: dict[str, Any]


class RegulatorySourceCitation(ExplainabilityBaseModel):
    chunk_id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    document_title: str | None = None
    regulator: str = Field(min_length=1)
    domain: str = Field(min_length=1)
    section_reference: str | None = None
    page_start: int | None = None
    page_end: int | None = None
    similarity_score: float = Field(ge=0, le=1)
    snippet: str = Field(min_length=1)
    supports_rule_ids: list[str] = Field(default_factory=list)


class ComplianceExplanationWithSources(ExplainabilityBaseModel):
    explanation: ComplianceExplanation
    regulatory_sources: list[RegulatorySourceCitation]
    retrieval_query: str
    limitations: list[str] = Field(default_factory=list)
