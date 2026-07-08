from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.operations.schemas import OperationsQueueResponse
from app.sla.schemas.sla_schemas import SLASummaryResponse

class ComplaintMonitoringResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    operations_queue: OperationsQueueResponse
    sla_summary: SLASummaryResponse
    escalation_counts: dict[str, int]
    generated_at: datetime
