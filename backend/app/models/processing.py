from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import JobItemStatus, JobStatus
from app.db.base import Base


class ComplaintProcessingRun(Base):
    __tablename__ = "complaint_processing_runs"
    __table_args__ = (
        UniqueConstraint("complaint_id", "attempt_number", name="uq_processing_run_attempt"),
        CheckConstraint("attempt_number > 0", name="ck_processing_run_attempt_positive"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid4()))
    complaint_id: Mapped[str] = mapped_column(
        ForeignKey("complaints.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status_outcome: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    trigger_reason: Mapped[str | None] = mapped_column(String(64))
    initiated_by: Mapped[str | None] = mapped_column(String(128))
    local_signals: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    bedrock_model: Mapped[str | None] = mapped_column(String(255))
    prompt_evidence: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB)
    ai_payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    error_category: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ProcessingJob(Base):
    __tablename__ = "processing_jobs"
    __table_args__ = (
        CheckConstraint("total_items >= 0", name="ck_processing_job_total_nonnegative"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid4()))
    job_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(32), default=JobStatus.QUEUED.value, nullable=False, index=True
    )
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)
    total_items: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ProcessingJobItem(Base):
    __tablename__ = "processing_job_items"
    __table_args__ = (
        UniqueConstraint("job_id", "complaint_id", name="uq_processing_job_complaint"),
        CheckConstraint("attempt_count >= 0", name="ck_processing_job_item_attempt_nonnegative"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid4()))
    job_id: Mapped[str] = mapped_column(
        ForeignKey("processing_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    complaint_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(32), default=JobItemStatus.QUEUED.value, nullable=False, index=True
    )
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)
    result_payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    attempt_history: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
