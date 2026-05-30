from pydantic import BaseModel, Field, field_validator

from app.core.constants import ChurnRisk, Sentiment


class ConfidenceScores(BaseModel):
    sentiment: int = Field(ge=0, le=100)
    category: int = Field(ge=0, le=100)
    urgency: int = Field(ge=0, le=100)
    churn_risk: int | None = Field(default=None, ge=0, le=100)
    draft_response: int | None = Field(default=None, ge=0, le=100)


class AIEnrichment(BaseModel):
    sentiment: Sentiment
    category: str = Field(min_length=1, max_length=255)
    urgency_score: int = Field(ge=0, le=100)
    churn_risk: ChurnRisk
    draft_response: str = Field(min_length=1)
    next_action: str = Field(min_length=1)
    similar_cases: list[str] = Field(default_factory=list)
    confidence_scores: ConfidenceScores
    ai_confidence: float = Field(ge=0, le=1)
    ai_reasoning: str | None = None

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
