from datetime import datetime
from typing import Any
from uuid import uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, CheckConstraint, DateTime, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import EMBEDDING_DIMENSIONS
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


class RegulatoryDocumentRecord(Base):
    __tablename__ = "regulatory_documents"
    __table_args__ = (
        UniqueConstraint("regulator", "document_title", "version", name="uq_regulatory_documents_identity"),
        CheckConstraint(
            "regulator IN ('RBI', 'NPCI', 'SEBI', 'IRDAI', 'BANK_INTERNAL')",
            name="ck_regulatory_documents_regulator",
        ),
        CheckConstraint(
            "document_type IN ('pdf', 'docx', 'txt', 'markdown', 'html')",
            name="ck_regulatory_documents_type",
        ),
        CheckConstraint(
            "status IN ('uploaded', 'processing', 'indexed', 'review_required', 'active', 'archived', 'failed')",
            name="ck_regulatory_documents_status",
        ),
        CheckConstraint(
            "effective_to IS NULL OR effective_from IS NULL OR effective_to >= effective_from",
            name="ck_regulatory_documents_effective_dates",
        ),
        Index("ix_regulatory_documents_regulator", "regulator"),
        Index("ix_regulatory_documents_status", "status"),
        Index("ix_regulatory_documents_document_type", "document_type"),
        Index("ix_regulatory_documents_effective_from", "effective_from"),
        Index("ix_regulatory_documents_uploaded_at", "uploaded_at"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid4()))
    regulator: Mapped[str] = mapped_column(String(32), nullable=False)
    document_title: Mapped[str] = mapped_column(String(255), nullable=False)
    document_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    effective_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="uploaded")
    uploaded_by: Mapped[str | None] = mapped_column(String(128))
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
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


class RegulatoryDocumentPageRecord(Base):
    __tablename__ = "regulatory_document_pages"
    __table_args__ = (
        Index("ix_regulatory_document_pages_document_id", "document_id"),
        Index("ix_regulatory_document_pages_page_number", "page_number"),
        UniqueConstraint("document_id", "page_number", name="uq_regulatory_document_pages_document_page"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid4()))
    document_id: Mapped[str] = mapped_column(String(64), nullable=False)
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    cleaned_text: Mapped[str] = mapped_column(Text, nullable=False)
    markdown_text: Mapped[str] = mapped_column(Text, nullable=False)
    extraction_status: Mapped[str] = mapped_column(String(32), nullable=False, default="extracted")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class RegulatoryDocumentMarkdownFileRecord(Base):
    __tablename__ = "regulatory_document_markdown_files"
    __table_args__ = (
        Index("ix_regulatory_document_markdown_files_document_id", "document_id"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid4()))
    document_id: Mapped[str] = mapped_column(String(64), nullable=False)
    markdown_path: Mapped[str] = mapped_column(Text, nullable=False)
    conversion_tool: Mapped[str] = mapped_column(String(128), nullable=False)
    conversion_status: Mapped[str] = mapped_column(String(32), nullable=False, default="converted")
    conversion_warnings: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
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


class RegulatoryKnowledgeChunkRecord(Base):
    __tablename__ = "regulatory_knowledge_chunks"
    __table_args__ = (
        CheckConstraint(
            "regulator IN ('RBI', 'NPCI', 'SEBI', 'IRDAI', 'BANK_INTERNAL')",
            name="ck_regulatory_knowledge_chunks_regulator",
        ),
        CheckConstraint(
            "status IN ('draft', 'active', 'archived')",
            name="ck_regulatory_knowledge_chunks_status",
        ),
        CheckConstraint(
            "page_end IS NULL OR page_start IS NULL OR page_end >= page_start",
            name="ck_regulatory_knowledge_chunks_page_window",
        ),
        CheckConstraint(
            "effective_to IS NULL OR effective_from IS NULL OR effective_to >= effective_from",
            name="ck_regulatory_knowledge_chunks_effective_dates",
        ),
        Index("ix_regulatory_knowledge_chunks_document_id", "document_id"),
        Index("ix_regulatory_knowledge_chunks_regulator", "regulator"),
        Index("ix_regulatory_knowledge_chunks_domain", "domain"),
        Index("ix_regulatory_knowledge_chunks_status", "status"),
        Index("ix_regulatory_knowledge_chunks_effective_from", "effective_from"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid4()))
    document_id: Mapped[str] = mapped_column(String(64), nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    regulator: Mapped[str] = mapped_column(String(32), nullable=False)
    domain: Mapped[str] = mapped_column(String(128), nullable=False, default="unknown")
    section_reference: Mapped[str | None] = mapped_column(String(255))
    page_start: Mapped[int | None] = mapped_column(Integer)
    page_end: Mapped[int | None] = mapped_column(Integer)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    keywords: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    effective_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    embedding_model: Mapped[str | None] = mapped_column(String(128))
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIMENSIONS))
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


Index(
    "ix_regulatory_knowledge_chunks_embedding_hnsw_cosine",
    RegulatoryKnowledgeChunkRecord.embedding,
    postgresql_using="hnsw",
    postgresql_ops={"embedding": "vector_cosine_ops"},
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
