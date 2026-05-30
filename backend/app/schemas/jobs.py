from datetime import datetime

from pydantic import BaseModel, Field


class CreateProcessingJobRequest(BaseModel):
    complaint_ids: list[str] = Field(min_length=1)


class JobCounts(BaseModel):
    queued: int = 0
    running: int = 0
    completed: int = 0
    human_review: int = 0
    failed: int = 0


class JobItemResponse(BaseModel):
    complaint_id: str
    status: str
    attempt_count: int
    error_message: str | None = None
    attempt_history: list[dict] = Field(default_factory=list)


class ProcessingJobResponse(BaseModel):
    job_id: str
    job_type: str
    status: str
    total_items: int
    counts: JobCounts
    created_by: str
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    items: list[JobItemResponse] = Field(default_factory=list)
