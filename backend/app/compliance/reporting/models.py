from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ReportingBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ComplianceReportField(ReportingBaseModel):
    field_key: str = Field(min_length=1)
    display_label: str = Field(min_length=1)
    field_type: Literal["string", "float", "datetime", "list", "boolean"]
    required_for_regulatory: bool
    source_module: str = Field(min_length=1)
    notes: str = Field(min_length=1)


class ComplianceReportRecord(ReportingBaseModel):
    complaint_id: str
    evaluated_at: datetime
    compliance_risk_level: str
    dominant_rule_id: str
    rules_triggered: list[str]
    required_actions: list[str]
    regulatory_breach: bool
    sla_compliance_status: str
    evidence_summary: list[str]
    audit_trail: dict[str, Any]
    export_flags: dict[str, bool]
    category: str | None = None


class ComplianceReportFilter(ReportingBaseModel):
    risk_levels: list[str] = Field(default_factory=list)
    regulatory_breach_only: bool = False
    rule_ids: list[str] = Field(default_factory=list)
    sla_statuses: list[str] = Field(default_factory=list)
    date_from: datetime | None = None
    date_to: datetime | None = None
    category: str | None = None
    required_action_contains: str | None = None
    product: str | None = None
    company: str | None = None
    channel: str | None = None
    escalation_reason: str | None = None
    review_outcome: str | None = None
