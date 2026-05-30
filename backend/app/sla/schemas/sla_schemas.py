from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.constants import ChurnRisk
from app.schemas.common import Pagination


class SLAGroupSortBy(StrEnum):
    TIMELY_RATE = "timely_rate"
    TOTAL = "total"
    UNTIMELY_COUNT = "untimely_count"


class SLATrendGranularity(StrEnum):
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class SLABaseSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=True)


class SLASummaryQuery(SLABaseSchema):
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
    def validate_date_range(self) -> "SLASummaryQuery":
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValueError("date_from must be less than or equal to date_to")
        return self


class SLAGroupedQuery(SLABaseSchema):
    date_from: datetime | None = None
    date_to: datetime | None = None
    limit: int = Field(default=20, ge=1, le=100)
    sort_by: SLAGroupSortBy = SLAGroupSortBy.TIMELY_RATE

    @model_validator(mode="after")
    def validate_date_range(self) -> "SLAGroupedQuery":
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValueError("date_from must be less than or equal to date_to")
        return self


class SLABreachRiskQuery(Pagination, SLABaseSchema):
    urgency_threshold: int = Field(default=70, ge=0, le=100)
    churn_risk: ChurnRisk | None = None


class SLATrendQuery(SLABaseSchema):
    granularity: SLATrendGranularity = SLATrendGranularity.MONTHLY
    date_from: datetime | None = None
    date_to: datetime | None = None
    product: str | None = Field(default=None, max_length=255)

    @field_validator("product")
    @classmethod
    def clean_optional_product(cls, value: str | None) -> str | None:
        if value is None:
            return value
        cleaned = value.strip()
        return cleaned or None

    @model_validator(mode="after")
    def validate_date_range(self) -> "SLATrendQuery":
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValueError("date_from must be less than or equal to date_to")
        return self


class SLASummaryResponse(SLABaseSchema):
    total_complaints: int
    timely_count: int
    untimely_count: int
    timely_rate_pct: float
    avg_urgency_score: float | None = None
    high_urgency_untimely_count: int
    period_from: datetime | None = None
    period_to: datetime | None = None


class SLAGroupedItem(SLABaseSchema):
    product: str | None = None
    channel: str | None = None
    total: int
    timely: int
    untimely: int
    timely_rate_pct: float
    avg_urgency_score: float | None = None


class SLAGroupedResponse(SLABaseSchema):
    items: list[SLAGroupedItem]
    count: int


class SLABreachRiskItem(SLABaseSchema):
    complaint_id: str
    source_complaint_id: str | None = None
    channel: str | None = None
    product: str | None = None
    timely_response: bool | None = None
    date_received: datetime | None = None
    urgency_score: int | None = None
    churn_risk: ChurnRisk | None = None
    processed_at: datetime | None = None
    created_at: datetime


class SLABreachRiskResponse(SLABaseSchema):
    items: list[SLABreachRiskItem]
    total: int
    limit: int
    offset: int


class SLATrendItem(SLABaseSchema):
    period: str
    total: int
    timely: int
    untimely: int
    timely_rate_pct: float


class SLATrendResponse(SLABaseSchema):
    granularity: SLATrendGranularity
    items: list[SLATrendItem]
