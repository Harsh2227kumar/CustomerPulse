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

class TrendByCategoryPoint(BaseModel):
    period: str
    category: str
    count: int


class TrendByCategoryResponse(BaseModel):
    items: list[TrendByCategoryPoint]
    granularity: str


class TrendByChannelPoint(BaseModel):
    period: str
    channel: str
    count: int


class TrendByChannelResponse(BaseModel):
    items: list[TrendByChannelPoint]
    granularity: str


class BottleneckMetricsResponse(BaseModel):
    avg_intake_to_ai_hours: float | None
    avg_ai_to_review_hours: float | None
    avg_intake_to_review_hours: float | None
    processed_count: int
    reviewed_count: int


class RecurringIssuePhrase(BaseModel):
    phrase: str
    count: int
    product: str | None
    category: str | None


class RecurringPhrasesResponse(BaseModel):
    items: list[RecurringIssuePhrase]


class ProductSpikeItem(BaseModel):
    product: str
    recent_count: int
    previous_count: int
    growth_rate: float
    spike_score: float


class ProductSpikesResponse(BaseModel):
    items: list[ProductSpikeItem]


class DuplicateThemeItem(BaseModel):
    group_id: str
    product: str | None
    category: str | None
    issue: str | None
    member_count: int
    created_at: datetime


class DuplicateThemesResponse(BaseModel):
    items: list[DuplicateThemeItem]


class BusinessImpactKPIsResponse(BaseModel):
    auto_resolution_pct: float
    avg_ai_processing_time_sec: float | None
    avg_human_resolution_time_sec: float | None
    timely_response_pct: float
    current_breach_rate_pct: float
    previous_breach_rate_pct: float
    breach_reduction_rate_pct: float
    total_processed: int
    total_reviewed: int
    workload_saved_hours: float


