from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.core.constants import ChurnRisk, Sentiment
from app.schemas.ai_response import ConfidenceScores
from app.schemas.common import Pagination


class ComplaintProcessRequest(BaseModel):
    complaint_id: str = Field(min_length=1, max_length=128)
    narrative: str = Field(min_length=1)
    channel: str | None = Field(default=None, max_length=64)
    product: str | None = Field(default=None, max_length=255)
    issue: str | None = Field(default=None, max_length=255)
    company: str | None = Field(default=None, max_length=255)

    @field_validator("complaint_id", "narrative")
    @classmethod
    def clean_required_strings(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("value must not be blank")
        return cleaned

    @field_validator("channel", "product", "issue", "company")
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
    churn_risk: ChurnRisk | None = None
    urgency_min: int | None = Field(default=None, ge=0, le=100)
    urgency_max: int | None = Field(default=None, ge=0, le=100)
    date_received_min: datetime | None = None
    date_received_max: datetime | None = None
    timely_response: bool | None = None
    search: str | None = None
    sort_by: str = Field(default="created_at")
    sort_direction: str = Field(default="desc", pattern="^(asc|desc)$")


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


class ComplaintListResponse(BaseModel):
    items: list[ComplaintListItem]
    limit: int
    offset: int
    count: int
