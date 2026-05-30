from datetime import datetime
from uuid import uuid4

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DuplicateGroup(Base):
    __tablename__ = "duplicate_groups"
    __table_args__ = (
        CheckConstraint(
            "detection_type IN ('exact', 'near')",
            name="ck_duplicate_groups_detection_type",
        ),
        CheckConstraint(
            "status IN ('detected', 'merged', 'rejected')",
            name="ck_duplicate_groups_status",
        ),
        Index("ix_duplicate_groups_detection_type", "detection_type"),
        Index("ix_duplicate_groups_status", "status"),
        Index("ix_duplicate_groups_created_at", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid4()))
    detection_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="detected", nullable=False)
    exact_hash: Mapped[str | None] = mapped_column(String(32), index=True)
    similarity_threshold: Mapped[float | None] = mapped_column(Float)
    canonical_complaint_pk: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("complaints.id", ondelete="SET NULL"),
    )
    merged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)
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


class DuplicateMember(Base):
    __tablename__ = "duplicate_members"
    __table_args__ = (
        UniqueConstraint("group_id", "complaint_pk", name="uq_duplicate_members_group_complaint"),
        Index("ix_duplicate_members_group_id", "group_id"),
        Index("ix_duplicate_members_complaint_pk", "complaint_pk"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid4()))
    group_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("duplicate_groups.id", ondelete="CASCADE"),
        nullable=False,
    )
    complaint_pk: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("complaints.id", ondelete="CASCADE"),
        nullable=False,
    )
    similarity_score: Mapped[float | None] = mapped_column(Float)
    is_primary: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
