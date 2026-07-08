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
    job_id: str | None = None
    complaint_id: str
    status: str
    attempt_count: int
    error_message: str | None = None
    attempt_history: list[dict] = Field(default_factory=list)
    started_at: datetime | None = None
    finished_at: datetime | None = None


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


class JobListResponse(BaseModel):
    items: list[ProcessingJobResponse]
    total_count: int
    limit: int
    offset: int


class ContinuousProcessingStatus(BaseModel):
    running: bool
    stopping: bool = False
    current_job_id: str | None = None
    current_complaint_id: str | None = None
    processed_count: int = 0
    last_message: str | None = None
    history: list[JobItemResponse] = Field(default_factory=list)


