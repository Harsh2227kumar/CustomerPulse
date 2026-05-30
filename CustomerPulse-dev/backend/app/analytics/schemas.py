from datetime import datetime

from pydantic import BaseModel


class TrendPoint(BaseModel):
    period: str
    count: int


class TrendResponse(BaseModel):
    items: list[TrendPoint]
    granularity: str


class ProductSummaryRow(BaseModel):
    product: str | None
    category: str | None
    count: int
    avg_urgency: float | None


class ProductSummaryResponse(BaseModel):
    items: list[ProductSummaryRow]


class HighUrgencyItem(BaseModel):
    complaint_id: str
    narrative: str
    product: str | None
    channel: str | None
    urgency_score: int
    sentiment: str | None
    created_at: datetime


class HighUrgencyResponse(BaseModel):
    items: list[HighUrgencyItem]
    count: int
    limit: int
    offset: int

