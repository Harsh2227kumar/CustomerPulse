"""Add regulatory RAG processing outputs.

Revision ID: 0003_regulatory_rag_outputs
Revises: 0002_regulatory_documents
Create Date: 2026-06-30
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
from pgvector.sqlalchemy import Vector
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from app.core.constants import EMBEDDING_DIMENSIONS


revision: str = "0003_regulatory_rag_outputs"
down_revision: Union[str, None] = "0002_regulatory_documents"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "regulatory_document_pages",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("document_id", sa.String(length=64), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("cleaned_text", sa.Text(), nullable=False),
        sa.Column("markdown_text", sa.Text(), nullable=False),
        sa.Column("extraction_status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_id", "page_number", name="uq_regulatory_document_pages_document_page"),
    )
    op.create_index("ix_regulatory_document_pages_document_id", "regulatory_document_pages", ["document_id"])
    op.create_index("ix_regulatory_document_pages_page_number", "regulatory_document_pages", ["page_number"])

    op.create_table(
        "regulatory_document_markdown_files",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("document_id", sa.String(length=64), nullable=False),
        sa.Column("markdown_path", sa.Text(), nullable=False),
        sa.Column("conversion_tool", sa.String(length=128), nullable=False),
        sa.Column("conversion_status", sa.String(length=32), nullable=False),
        sa.Column("conversion_warnings", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_regulatory_document_markdown_files_document_id",
        "regulatory_document_markdown_files",
        ["document_id"],
    )

    op.create_table(
        "regulatory_knowledge_chunks",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("document_id", sa.String(length=64), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("regulator", sa.String(length=32), nullable=False),
        sa.Column("domain", sa.String(length=128), nullable=False),
        sa.Column("section_reference", sa.String(length=255), nullable=True),
        sa.Column("page_start", sa.Integer(), nullable=True),
        sa.Column("page_end", sa.Integer(), nullable=True),
        sa.Column("chunk_text", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("keywords", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("effective_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("embedding_model", sa.String(length=128), nullable=True),
        sa.Column("embedding", Vector(EMBEDDING_DIMENSIONS), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "regulator IN ('RBI', 'NPCI', 'SEBI', 'IRDAI', 'BANK_INTERNAL')",
            name="ck_regulatory_knowledge_chunks_regulator",
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'active', 'archived')",
            name="ck_regulatory_knowledge_chunks_status",
        ),
        sa.CheckConstraint(
            "page_end IS NULL OR page_start IS NULL OR page_end >= page_start",
            name="ck_regulatory_knowledge_chunks_page_window",
        ),
        sa.CheckConstraint(
            "effective_to IS NULL OR effective_from IS NULL OR effective_to >= effective_from",
            name="ck_regulatory_knowledge_chunks_effective_dates",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_regulatory_knowledge_chunks_document_id", "regulatory_knowledge_chunks", ["document_id"])
    op.create_index("ix_regulatory_knowledge_chunks_regulator", "regulatory_knowledge_chunks", ["regulator"])
    op.create_index("ix_regulatory_knowledge_chunks_domain", "regulatory_knowledge_chunks", ["domain"])
    op.create_index("ix_regulatory_knowledge_chunks_status", "regulatory_knowledge_chunks", ["status"])
    op.create_index("ix_regulatory_knowledge_chunks_effective_from", "regulatory_knowledge_chunks", ["effective_from"])
    op.create_index(
        "ix_regulatory_knowledge_chunks_embedding_hnsw_cosine",
        "regulatory_knowledge_chunks",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )


def downgrade() -> None:
    op.drop_index("ix_regulatory_knowledge_chunks_embedding_hnsw_cosine", table_name="regulatory_knowledge_chunks")
    op.drop_index("ix_regulatory_knowledge_chunks_effective_from", table_name="regulatory_knowledge_chunks")
    op.drop_index("ix_regulatory_knowledge_chunks_status", table_name="regulatory_knowledge_chunks")
    op.drop_index("ix_regulatory_knowledge_chunks_domain", table_name="regulatory_knowledge_chunks")
    op.drop_index("ix_regulatory_knowledge_chunks_regulator", table_name="regulatory_knowledge_chunks")
    op.drop_index("ix_regulatory_knowledge_chunks_document_id", table_name="regulatory_knowledge_chunks")
    op.drop_table("regulatory_knowledge_chunks")
    op.drop_index("ix_regulatory_document_markdown_files_document_id", table_name="regulatory_document_markdown_files")
    op.drop_table("regulatory_document_markdown_files")
    op.drop_index("ix_regulatory_document_pages_page_number", table_name="regulatory_document_pages")
    op.drop_index("ix_regulatory_document_pages_document_id", table_name="regulatory_document_pages")
    op.drop_table("regulatory_document_pages")
