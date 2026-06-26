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

class ComplaintVolumeSummary(BaseModel):
    total_count: int
    avg_per_period: float
    peak_period: str | None = None
    peak_count: int
    high_urgency_count: int
    human_review_count: int
    negative_count: int
    avg_urgency: float | None = None


class ComplaintVolumeTimelineItem(BaseModel):
    period: str
    total: int
    high_urgency: int
    human_review: int
    negative: int
    timely: int
    untimely: int
    avg_urgency: float | None = None


class ComplaintVolumeGroupItem(BaseModel):
    group: str
    count: int
    avg_urgency: float | None = None
    high_urgency: int
    negative: int
    human_review: int


class ComplaintVolumeHeatmapItem(BaseModel):
    product: str
    channel: str
    count: int
    avg_urgency: float | None = None


class ComplaintVolumeMixItem(BaseModel):
    label: str
    count: int


class ComplaintVolumeSampleItem(BaseModel):
    complaint_id: str
    product: str | None = None
    channel: str | None = None
    category: str | None = None
    sentiment: str | None = None
    ai_status: str
    urgency_score: int | None = None
    date_received: datetime | None = None
    narrative: str


class ComplaintVolumeInsightsResponse(BaseModel):
    granularity: str
    group_by: str
    summary: ComplaintVolumeSummary
    timeline: list[ComplaintVolumeTimelineItem]
    groups: list[ComplaintVolumeGroupItem]
    heatmap: list[ComplaintVolumeHeatmapItem]
    sentiment_mix: list[ComplaintVolumeMixItem]
    status_mix: list[ComplaintVolumeMixItem]
    samples: list[ComplaintVolumeSampleItem]

