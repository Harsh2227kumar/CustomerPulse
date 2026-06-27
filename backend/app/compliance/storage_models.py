from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import Boolean, CheckConstraint, DateTime, Index, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ComplianceEvidenceRecord(Base):
    __tablename__ = "compliance_evidence_records"
    __table_args__ = (
        CheckConstraint(
            "risk_level IN ('low', 'medium', 'high', 'critical')",
            name="ck_compliance_evidence_risk_level",
        ),
        Index("ix_compliance_evidence_complaint_id", "complaint_id"),
        Index("ix_compliance_evidence_source_complaint_id", "source_complaint_id"),
        Index("ix_compliance_evidence_risk_level", "risk_level"),
        Index("ix_compliance_evidence_regulatory_flag", "regulatory_flag"),
        Index("ix_compliance_evidence_evaluated_at", "evaluated_at"),
        Index("ix_compliance_evidence_created_at", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid4()))
    complaint_id: Mapped[str] = mapped_column(String(128), nullable=False)
    source_complaint_id: Mapped[str | None] = mapped_column(String(128))
    risk_level: Mapped[str] = mapped_column(String(32), nullable=False)
    required_action: Mapped[str | None] = mapped_column(String(64))
    regulatory_flag: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    regulatory_interpretation: Mapped[str] = mapped_column(String(128), nullable=False)
    triggered_rules: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    evidence_snippets: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    required_actions: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    reason_codes: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    result_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
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


class ComplianceRuleRecord(Base):
    __tablename__ = "compliance_rules"
    __table_args__ = (
        UniqueConstraint("rule_id", "version", name="uq_compliance_rules_rule_id_version"),
        CheckConstraint(
            "regulator IN ('RBI', 'NPCI', 'SEBI', 'IRDAI', 'BANK_INTERNAL')",
            name="ck_compliance_rules_regulator",
        ),
        CheckConstraint(
            "status IN ('draft', 'active', 'inactive', 'retired')",
            name="ck_compliance_rules_status",
        ),
        CheckConstraint(
            "severity IN ('low', 'medium', 'high', 'critical')",
            name="ck_compliance_rules_severity",
        ),
        CheckConstraint(
            "effective_to IS NULL OR effective_to >= effective_from",
            name="ck_compliance_rules_effective_dates",
        ),
        Index("ix_compliance_rules_rule_id", "rule_id"),
        Index("ix_compliance_rules_regulator", "regulator"),
        Index("ix_compliance_rules_domain", "domain"),
        Index("ix_compliance_rules_status", "status"),
        Index("ix_compliance_rules_effective_from", "effective_from"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid4()))
    rule_id: Mapped[str] = mapped_column(String(128), nullable=False)
    rule_name: Mapped[str] = mapped_column(String(255), nullable=False)
    regulator: Mapped[str] = mapped_column(String(32), nullable=False)
    domain: Mapped[str] = mapped_column(String(128), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    evaluation_type: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    reason_code: Mapped[str | None] = mapped_column(String(64))
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    supersedes_rule_record_id: Mapped[str | None] = mapped_column(String(64))
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


class ReasonCodeRecord(Base):
    __tablename__ = "reason_codes"
    __table_args__ = (
        UniqueConstraint("code", name="uq_reason_codes_code"),
        CheckConstraint(
            "severity IN ('low', 'medium', 'high', 'critical')",
            name="ck_reason_codes_severity",
        ),
        CheckConstraint(
            "status IN ('active', 'inactive', 'retired')",
            name="ck_reason_codes_status",
        ),
        Index("ix_reason_codes_code", "code"),
        Index("ix_reason_codes_status", "status"),
        Index("ix_reason_codes_severity", "severity"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid4()))
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
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
