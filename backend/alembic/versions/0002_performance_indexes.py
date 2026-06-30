"""Add production query performance indexes.

Revision ID: 0002_performance_indexes
Revises: 0001_initial_schema
Create Date: 2026-07-01
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op


revision: str = "0002_performance_indexes"
down_revision: Union[str, None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_complaints_created_at_id "
        "ON complaints (created_at DESC, id ASC)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_complaints_completed_date "
        "ON complaints (ai_status, date_received)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_complaints_completed_product_date "
        "ON complaints (ai_status, product, date_received)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_complaints_completed_channel_date "
        "ON complaints (ai_status, channel, date_received)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_complaints_urgency_created "
        "ON complaints (urgency_score DESC, created_at DESC)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_complaints_ops_queue_priority "
        "ON complaints (urgency_score DESC, created_at ASC) "
        "WHERE ai_status = 'human_review' OR urgency_score >= 70"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_escalations_status_complaint_pk "
        "ON escalations (status, complaint_pk)"
    )


def downgrade() -> None:
    op.drop_index("ix_escalations_status_complaint_pk", table_name="escalations", if_exists=True)
    op.drop_index("ix_complaints_ops_queue_priority", table_name="complaints", if_exists=True)
    op.drop_index("ix_complaints_urgency_created", table_name="complaints", if_exists=True)
    op.drop_index("ix_complaints_completed_channel_date", table_name="complaints", if_exists=True)
    op.drop_index("ix_complaints_completed_product_date", table_name="complaints", if_exists=True)
    op.drop_index("ix_complaints_completed_date", table_name="complaints", if_exists=True)
    op.drop_index("ix_complaints_created_at_id", table_name="complaints", if_exists=True)