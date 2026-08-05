"""add payment execution tracking columns

Revision ID: 002_payment_execution_columns
Revises: 001_core_tables
Create Date: 2026-08-06
"""

import sqlalchemy as sa
from alembic import op

revision = "002_payment_execution_columns"
down_revision = "001_core_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("payment_requests")}
    if "keeperhub_execution_id" not in columns:
        op.add_column(
            "payment_requests",
            sa.Column("keeperhub_execution_id", sa.String(length=128), nullable=True),
        )
    if "transaction_hash" not in columns:
        op.add_column(
            "payment_requests",
            sa.Column("transaction_hash", sa.String(length=66), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("payment_requests")}
    if "transaction_hash" in columns:
        op.drop_column("payment_requests", "transaction_hash")
    if "keeperhub_execution_id" in columns:
        op.drop_column("payment_requests", "keeperhub_execution_id")
