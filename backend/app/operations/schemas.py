from datetime import datetime

from pydantic import BaseModel

from app.schemas.common import Pagination


class OperationsQueueItem(BaseModel):
    complaint_id: str
    source_complaint_id: str | None = None
    channel: str | None = None
    product: str | None = None
    urgency_score: int | None = None
    churn_risk: str | None = None
    ai_status: str
    human_review_reason: str | None = None
    has_open_escalation: bool
    escalation_id: str | None = None
    created_at: datetime
    processed_at: datetime | None = None


class OperationsQueueQuery(Pagination):
    pass


class OperationsQueueResponse(BaseModel):
    items: list[OperationsQueueItem]
    total: int
    limit: int
    offset: int
