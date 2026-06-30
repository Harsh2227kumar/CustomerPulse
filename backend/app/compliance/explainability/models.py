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
