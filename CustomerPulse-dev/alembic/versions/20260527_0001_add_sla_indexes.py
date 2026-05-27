"""add sla indexes

Revision ID: 20260527_0001
Revises:
Create Date: 2026-05-27 00:01:00
"""

from collections.abc import Sequence

from alembic import op


revision: str = "20260527_0001"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute(
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_complaints_timely_response_product
            ON complaints(product, timely_response)
            WHERE ai_status = 'completed';
            """
        )
        op.execute(
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_complaints_date_urgency_sla
            ON complaints(date_received, urgency_score, timely_response)
            WHERE date_received IS NOT NULL;
            """
        )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_complaints_date_urgency_sla;")
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_complaints_timely_response_product;")
