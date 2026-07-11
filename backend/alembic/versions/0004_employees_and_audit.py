"""Employees and audit logs schema.

Revision ID: 0004_employees_and_audit
Revises: 0003_regulatory_rag_outputs
Create Date: 2026-06-30
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Sequence, Union

from alembic import op

BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db.base import Base
from app.employees.models import Department, Employee, AuditLog  # noqa: F401

revision: str = "0004_employees_and_audit"
down_revision: Union[str, None] = "0003_regulatory_rag_outputs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("CREATE SEQUENCE IF NOT EXISTS employee_id_seq START 1;")
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    op.drop_table("audit_logs")
    op.drop_table("employees")
    op.drop_table("departments")
    if bind.dialect.name == "postgresql":
        op.execute("DROP SEQUENCE IF EXISTS employee_id_seq;")

