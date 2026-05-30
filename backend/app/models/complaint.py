from datetime import datetime
from typing import Any
from uuid import uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Float, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import EMBEDDING_DIMENSIONS, ProcessingStatus
from app.db.base import Base


class Complaint(Base):
    __tablename__ = "complaints"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid4()))
    source_complaint_id: Mapped[str | None] = mapped_column(String(128), unique=True, index=True)
    narrative: Mapped[str] = mapped_column(Text, nullable=False)
    channel: Mapped[str | None] = mapped_column(String(64), index=True)
    product: Mapped[str | None] = mapped_column(String(255), index=True)
    sub_product: Mapped[str | None] = mapped_column(String(255))
    issue: Mapped[str | None] = mapped_column(String(255), index=True)
    sub_issue: Mapped[str | None] = mapped_column(String(255))
    company: Mapped[str | None] = mapped_column(String(255), index=True)
    company_response: Mapped[str | None] = mapped_column(String(255))
    timely_response: Mapped[bool | None] = mapped_column(index=True)
    date_received: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)

    sentiment: Mapped[str | None] = mapped_column(String(32), index=True)
    category: Mapped[str | None] = mapped_column(String(255), index=True)
    urgency_score: Mapped[int | None] = mapped_column(Integer, index=True)
    churn_risk: Mapped[str | None] = mapped_column(String(32), index=True)
    draft_response: Mapped[str | None] = mapped_column(Text)
    next_action: Mapped[str | None] = mapped_column(Text)
    confidence_scores: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    ai_confidence: Mapped[float | None] = mapped_column(Float)
    ai_reasoning: Mapped[str | None] = mapped_column(Text)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIMENSIONS))
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    ai_status: Mapped[str] = mapped_column(
        String(32),
        default=ProcessingStatus.PENDING.value,
        nullable=False,
        index=True,
    )
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
