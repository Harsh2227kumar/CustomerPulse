from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator

from app.core.constants import ChurnRisk, ProcessingStatus, Sentiment
from app.feedback.schemas import FeedbackAction


class ComplaintCSVExportQuery(BaseModel):
    date_from: datetime | None = None
    date_to: datetime | None = None
    product: str | None = Field(default=None, max_length=255)
    channel: str | None = Field(default=None, max_length=64)
    sentiment: Sentiment | None = None
    urgency_min: int | None = Field(default=None, ge=0, le=100)
    urgency_max: int | None = Field(default=None, ge=0, le=100)
    churn_risk: ChurnRisk | None = None
    ai_status: ProcessingStatus | None = None
    limit: int = Field(default=1000, ge=1, le=5000)

    @field_validator("product", "channel")
    @classmethod
    def clean_optional_strings(cls, value: str | None) -> str | None:
        if value is None:
            return value
        cleaned = value.strip()
        return cleaned or None

    @model_validator(mode="after")
    def validate_ranges(self) -> "ComplaintCSVExportQuery":
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValueError("date_from must be less than or equal to date_to")
        if (
            self.urgency_min is not None
            and self.urgency_max is not None
            and self.urgency_min > self.urgency_max
        ):
            raise ValueError("urgency_min must be less than or equal to urgency_max")
        return self


class ComplaintPDFExportQuery(BaseModel):
    date_from: datetime | None = None
    date_to: datetime | None = None
    product: str | None = Field(default=None, max_length=255)
    channel: str | None = Field(default=None, max_length=64)

    @field_validator("product", "channel")
    @classmethod
    def clean_optional_strings(cls, value: str | None) -> str | None:
        if value is None:
            return value
        cleaned = value.strip()
        return cleaned or None

    @model_validator(mode="after")
    def validate_dates(self) -> "ComplaintPDFExportQuery":
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValueError("date_from must be less than or equal to date_to")
        return self


class AnalyticsCSVExportQuery(BaseModel):
    date_from: datetime | None = None
    date_to: datetime | None = None

    @model_validator(mode="after")
    def validate_dates(self) -> "AnalyticsCSVExportQuery":
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValueError("date_from must be less than or equal to date_to")
        return self


class FeedbackCSVExportQuery(BaseModel):
    date_from: datetime | None = None
    date_to: datetime | None = None
    action_type: FeedbackAction | None = None
    limit: int = Field(default=500, ge=1, le=2000)

    @model_validator(mode="after")
    def validate_dates(self) -> "FeedbackCSVExportQuery":
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValueError("date_from must be less than or equal to date_to")
        return self

