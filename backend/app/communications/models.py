from datetime import datetime
from uuid import uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional

from app.db.base import Base


class CommunicationHistory(Base):
    __tablename__ = "communication_history"
    __table_args__ = (
        CheckConstraint(
            "entry_type IN ('system', 'note', 'escalation')",
            name="ck_communication_history_entry_type",
        ),
        Index("ix_communication_history_complaint_created_at", "complaint_pk", "created_at"),
        Index("ix_communication_history_event_code", "event_code"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid4()))
    complaint_pk: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("complaints.id", ondelete="CASCADE"),
        nullable=False,
    )
    entry_type: Mapped[str] = mapped_column(String(32), nullable=False)
    event_code: Mapped[Optional[str]] = mapped_column(String(64))
    message: Mapped[str] = mapped_column(Text, nullable=False)
    actor: Mapped[Optional[str]] = mapped_column(String(128))
    context: Mapped[Optional[dict]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
