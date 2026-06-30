from datetime import datetime
from uuid import uuid4

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Escalation(Base):
    __tablename__ = "escalations"
    __table_args__ = (
        CheckConstraint(
            "status IN ('open', 'resolved')",
            name="ck_escalations_status",
        ),
        CheckConstraint(
            "trigger_type IN ('auto', 'manual')",
            name="ck_escalations_trigger_type",
        ),
        Index("ix_escalations_complaint_pk_status", "complaint_pk", "status"),
        Index("ix_escalations_status_complaint_pk", "status", "complaint_pk"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid4()))
    complaint_pk: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("complaints.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(32), default="open", nullable=False)
    trigger_type: Mapped[str] = mapped_column(String(16), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    urgency_score_snapshot: Mapped[int | None] = mapped_column(Integer)
    churn_risk_snapshot: Mapped[str | None] = mapped_column(String(32))
    ai_confidence_snapshot: Mapped[float | None] = mapped_column(Float)
    escalated_by: Mapped[str | None] = mapped_column(String(128))
    escalated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    resolved_by: Mapped[str | None] = mapped_column(String(128))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolution_notes: Mapped[str | None] = mapped_column(Text)
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
