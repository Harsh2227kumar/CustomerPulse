"""Add regulatory document repository.

Revision ID: 0002_regulatory_documents
Revises: 0001_initial_schema
Create Date: 2026-06-30
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0002_regulatory_documents"
down_revision: Union[str, None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "regulatory_documents",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("regulator", sa.String(length=32), nullable=False),
        sa.Column("document_title", sa.String(length=255), nullable=False),
        sa.Column("document_type", sa.String(length=32), nullable=False),
        sa.Column("source_filename", sa.String(length=255), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("effective_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("uploaded_by", sa.String(length=128), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "regulator IN ('RBI', 'NPCI', 'SEBI', 'IRDAI', 'BANK_INTERNAL')",
            name="ck_regulatory_documents_regulator",
        ),
        sa.CheckConstraint(
            "document_type IN ('pdf', 'docx', 'txt', 'markdown', 'html')",
            name="ck_regulatory_documents_type",
        ),
        sa.CheckConstraint(
            "status IN ('uploaded', 'processing', 'indexed', 'review_required', 'active', 'archived', 'failed')",
            name="ck_regulatory_documents_status",
        ),
        sa.CheckConstraint(
            "effective_to IS NULL OR effective_from IS NULL OR effective_to >= effective_from",
            name="ck_regulatory_documents_effective_dates",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("regulator", "document_title", "version", name="uq_regulatory_documents_identity"),
    )
    op.create_index("ix_regulatory_documents_regulator", "regulatory_documents", ["regulator"])
    op.create_index("ix_regulatory_documents_status", "regulatory_documents", ["status"])
    op.create_index("ix_regulatory_documents_document_type", "regulatory_documents", ["document_type"])
    op.create_index("ix_regulatory_documents_effective_from", "regulatory_documents", ["effective_from"])
    op.create_index("ix_regulatory_documents_uploaded_at", "regulatory_documents", ["uploaded_at"])


def downgrade() -> None:
    op.drop_index("ix_regulatory_documents_uploaded_at", table_name="regulatory_documents")
    op.drop_index("ix_regulatory_documents_effective_from", table_name="regulatory_documents")
    op.drop_index("ix_regulatory_documents_document_type", table_name="regulatory_documents")
    op.drop_index("ix_regulatory_documents_status", table_name="regulatory_documents")
    op.drop_index("ix_regulatory_documents_regulator", table_name="regulatory_documents")
    op.drop_table("regulatory_documents")
