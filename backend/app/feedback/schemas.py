from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import Pagination


class FeedbackAction(StrEnum):
    ACCEPTED = "accepted"
    EDITED = "edited"
    REJECTED = "rejected"
    ESCALATED = "escalated"


class HumanReviewOutcome(StrEnum):
    RESOLVED = "resolved"
    PENDING = "pending"
    ESCALATED_TIER2 = "escalated_tier2"
    CLOSED = "closed"


class AgentFeedbackUpsertRequest(BaseModel):
    agent_id: str = Field(min_length=1, max_length=255)
    feedback_action: FeedbackAction
    final_response: str | None = None
    action_used: bool | None = None
    human_review_outcome: HumanReviewOutcome
    similar_cases_useful: bool | None = None
    notes: str | None = None

    @field_validator("agent_id")
    @classmethod
    def clean_agent_id(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("value must not be blank")
        return cleaned

    @field_validator("final_response", "notes")
    @classmethod
    def clean_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return value
        cleaned = value.strip()
        return cleaned or None


class FeedbackRead(BaseModel):
    complaint_id: str
    agent_id: str
    feedback_action: FeedbackAction
    final_response: str | None = None
    action_used: bool | None = None
    human_review_outcome: HumanReviewOutcome
    similar_cases_useful: bool | None = None
    notes: str | None = None
    revision_count: int
    submitted_at: datetime
    updated_at: datetime


class FeedbackListQuery(Pagination):
    agent_id: str | None = None
    feedback_action: FeedbackAction | None = None

    @field_validator("agent_id")
    @classmethod
    def clean_optional_agent_id(cls, value: str | None) -> str | None:
        if value is None:
            return value
        cleaned = value.strip()
        return cleaned or None


class FeedbackListResponse(BaseModel):
    items: list[FeedbackRead]
    limit: int
    offset: int
    count: int
