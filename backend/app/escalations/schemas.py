from datetime import datetime
from pydantic import BaseModel, Field
from app.schemas.common import Pagination

class EscalationCreateRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=2000)

class EscalationResolveRequest(BaseModel):
    resolution_notes: str = Field(min_length=1, max_length=2000)

class EscalationRead(BaseModel):
    id: str
    complaint_id: str
    status: str
    trigger_type: str
    reason: str
    urgency_score_snapshot: int | None = None
    churn_risk_snapshot: str | None = None
    ai_confidence_snapshot: float | None = None
    escalated_by: str | None = None
    escalated_at: datetime
    resolved_by: str | None = None
    resolved_at: datetime | None = None
    resolution_notes: str | None = None
    created_at: datetime
    updated_at: datetime

class EscalationListQuery(Pagination):
    status: str | None = None
    trigger_type: str | None = None

class EscalationListResponse(BaseModel):
    items: list[EscalationRead]
    total: int
    limit: int
    offset: int
