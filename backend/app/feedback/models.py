from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AgentFeedback(Base):
    __tablename__ = "agent_feedback"
    __table_args__ = (
        UniqueConstraint("complaint_pk", name="uq_agent_feedback_complaint_pk"),
        CheckConstraint(
            "feedback_action IN ('accepted', 'edited', 'rejected', 'escalated')",
            name="ck_agent_feedback_action",
        ),
        Index("ix_agent_feedback_feedback_action", "feedback_action"),
        Index("ix_agent_feedback_submitted_at", "submitted_at"),
        Index("ix_agent_feedback_agent_id", "agent_id"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid4()))
    complaint_pk: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("complaints.id", ondelete="CASCADE"),
        nullable=False,
    )
    agent_id: Mapped[str] = mapped_column(String(255), nullable=False)
    feedback_action: Mapped[str] = mapped_column(String(32), nullable=False)
    final_response: Mapped[str | None] = mapped_column(Text)
    action_used: Mapped[bool | None] = mapped_column(Boolean)
    human_review_outcome: Mapped[str] = mapped_column(String(32), nullable=False)
    similar_cases_useful: Mapped[bool | None] = mapped_column(Boolean)
    notes: Mapped[str | None] = mapped_column(Text)
    revision_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(
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
