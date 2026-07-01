from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.core.constants import ChurnRisk, ProcessingStatus, ReviewReason, Sentiment
from app.compliance.explainability.models import ComplianceExplanationWithSources
from app.schemas.ai_response import ConfidenceScores, SimilarCaseEvidence
from app.schemas.common import Pagination


class ComplaintProcessRequest(BaseModel):
    complaint_id: str = Field(min_length=1, max_length=128)
    narrative: str = Field(min_length=1)
    channel: str | None = Field(default=None, max_length=64)
    product: str | None = Field(default=None, max_length=255)
    sub_product: str | None = Field(default=None, max_length=255)
    issue: str | None = Field(default=None, max_length=255)
    sub_issue: str | None = Field(default=None, max_length=255)
    company: str | None = Field(default=None, max_length=255)
    company_response: str | None = Field(default=None, max_length=255)
    timely_response: bool | None = Field(default=None)
    date_received: datetime | None = Field(default=None)
    category: str | None = Field(default=None, max_length=255)

    @field_validator("complaint_id", "narrative")
    @classmethod
    def clean_required_strings(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("value must not be blank")
        return cleaned

    @field_validator("channel", "product", "sub_product", "issue", "sub_issue", "company", "company_response", "category")
    @classmethod
    def clean_optional_strings(cls, value: str | None) -> str | None:
        if value is None:
            return value
        cleaned = value.strip()
        return cleaned or None


class ComplaintFilters(Pagination):
    sentiment: Sentiment | None = None
    channel: str | None = None
    product: str | None = None
    sub_product: str | None = Field(default=None, max_length=255)
    issue: str | None = None
    sub_issue: str | None = Field(default=None, max_length=255)
    company: str | None = Field(default=None, max_length=255)
    category: str | None = Field(default=None, max_length=255)
    churn_risk: ChurnRisk | None = None
    urgency_min: int | None = Field(default=None, ge=0, le=100)
    urgency_max: int | None = Field(default=None, ge=0, le=100)
    date_received_min: datetime | None = None
    date_received_max: datetime | None = None
    timely_response: bool | None = None
    ai_status: ProcessingStatus | None = None
    human_review_reason: ReviewReason | None = None
    search: str | None = Field(default=None, max_length=256)
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
    ] = "created_at"
    sort_direction: Literal["asc", "desc"] = "desc"

    @model_validator(mode="after")
    def valid_urgency_range(self) -> "ComplaintFilters":
        if (
            self.urgency_min is not None
            and self.urgency_max is not None
            and self.urgency_min > self.urgency_max
        ):
            raise ValueError("urgency_min must be less than or equal to urgency_max")
        if self.sort_by == "relevance" and not (self.search and self.search.strip()):
            raise ValueError("relevance sorting requires a non-empty search query")
        return self


class ComplaintAssignRequest(BaseModel):
    agent_id: str = Field(min_length=1, max_length=128)


class ComplaintListItem(BaseModel):
    complaint_id: str
    narrative: str
    channel: str | None = None
    product: str | None = None
    issue: str | None = None
    date_received: datetime | None = None
    timely_response: str | None = None
    sentiment: Sentiment | None = None
    category: str | None = None
    urgency_score: int | None = None
    churn_risk: ChurnRisk | None = None
    confidence_scores: ConfidenceScores | None = None
    processed_at: datetime | None = None
    ai_status: str
    human_review_reason: str | None = None
    human_review_created_at: datetime | None = None
    similar_cases: list[SimilarCaseEvidence] = Field(default_factory=list)
    sla_deadline: datetime | None = None
    sla_status: str | None = None
    assigned_agent_id: str | None = None



class ComplaintComplianceExplanationResponse(BaseModel):
    available: bool
    message: str
    complaint_id: str
    evidence_record_id: str | None = None
    risk_level: str | None = None
    regulatory_flag: bool | None = None
    required_action: str | None = None
    evaluated_at: datetime | None = None
    explanation_with_sources: ComplianceExplanationWithSources | None = None

class ComplaintListResponse(BaseModel):
    items: list[ComplaintListItem]
    limit: int
    offset: int
    count: int


class ProcessingRunItem(BaseModel):
    id: str
    attempt_number: int
    status_outcome: str
    trigger_reason: str | None = None
    initiated_by: str | None = None
    error_category: str | None = None
    created_at: datetime
    finished_at: datetime | None = None


class ComplaintDetail(ComplaintListItem):
    draft_response: str | None = None
    next_action: str | None = None
    ai_confidence: float | None = None
    ai_reasoning: str | None = None
    reviewed_at: datetime | None = None
    reviewer: str | None = None
    review_resolution: str | None = None
    approved_response: str | None = None
    review_notes: str | None = None
    embedding_model: str | None = None
    embedded_at: datetime | None = None
    processing_runs: list[ProcessingRunItem] = Field(default_factory=list)


class ApproveReviewRequest(BaseModel):
    approved_response: str | None = Field(default=None, min_length=1)
    notes: str | None = None


class ResolveReviewRequest(BaseModel):
    resolution: str = Field(min_length=1, max_length=64)
    notes: str | None = None

    @field_validator("resolution")
    @classmethod
    def clean_resolution(cls, value: str) -> str:
        return value.strip()
