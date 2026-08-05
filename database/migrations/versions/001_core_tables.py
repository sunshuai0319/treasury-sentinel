"""create core treasury tables

Revision ID: 001_core_tables
Revises:
Create Date: 2026-08-05
"""

import sqlalchemy as sa
from alembic import op

revision = "001_core_tables"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "vendors",
        sa.Column("vendor_id", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("risk_level", sa.String(length=32), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("wallet_address", sa.String(length=42), nullable=False),
        sa.Column("wallet_changed_recently", sa.Boolean(), nullable=False),
        sa.Column("max_single_payment_units", sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint("vendor_id"),
    )
    op.create_index("ix_vendors_status", "vendors", ["status"])

    op.create_table(
        "invoices",
        sa.Column("invoice_id", sa.String(length=64), nullable=False),
        sa.Column("vendor_id", sa.String(length=32), nullable=False),
        sa.Column("amount_units", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.String(length=16), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("recipient_address", sa.String(length=42), nullable=False),
        sa.Column("content_hash", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.PrimaryKeyConstraint("invoice_id"),
        sa.UniqueConstraint("content_hash", name="uq_invoices_content_hash"),
    )
    op.create_index("ix_invoices_vendor_id", "invoices", ["vendor_id"])
    op.create_index("ix_invoices_content_hash", "invoices", ["content_hash"])

    op.create_table(
        "vendor_wallet_history",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("vendor_id", sa.String(length=32), nullable=False),
        sa.Column("wallet_address", sa.String(length=42), nullable=False),
        sa.Column("changed_at", sa.DateTime(), nullable=False),
        sa.Column("changed_by", sa.String(length=128), nullable=False),
        sa.ForeignKeyConstraint(["vendor_id"], ["vendors.vendor_id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_vendor_wallet_history_vendor_id", "vendor_wallet_history", ["vendor_id"])

    op.create_table(
        "payment_requests",
        sa.Column("request_id", sa.String(length=64), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("vendor_id", sa.String(length=32), nullable=False),
        sa.Column("invoice_id", sa.String(length=64), nullable=False),
        sa.Column("amount_units", sa.BigInteger(), nullable=False),
        sa.Column("recipient_address", sa.String(length=42), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("final_action", sa.String(length=16), nullable=True),
        sa.Column("decision_hash", sa.String(length=66), nullable=True),
        sa.Column("keeperhub_execution_id", sa.String(length=128), nullable=True),
        sa.Column("transaction_hash", sa.String(length=66), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.invoice_id"]),
        sa.ForeignKeyConstraint(["vendor_id"], ["vendors.vendor_id"]),
        sa.PrimaryKeyConstraint("request_id"),
        sa.UniqueConstraint("idempotency_key", name="uq_payment_requests_idempotency"),
    )
    op.create_index("ix_payment_requests_vendor_id", "payment_requests", ["vendor_id"])
    op.create_index("ix_payment_requests_invoice_id", "payment_requests", ["invoice_id"])
    op.create_index("ix_payment_requests_status", "payment_requests", ["status"])

    op.create_table(
        "approvals",
        sa.Column("approval_id", sa.String(length=64), nullable=False),
        sa.Column("request_id", sa.String(length=64), nullable=False),
        sa.Column("approver", sa.String(length=128), nullable=False),
        sa.Column("decision", sa.String(length=16), nullable=False),
        sa.Column("reason", sa.String(length=512), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["request_id"], ["payment_requests.request_id"]),
        sa.PrimaryKeyConstraint("approval_id"),
    )
    op.create_index("ix_approvals_request_id", "approvals", ["request_id"])

    op.create_table(
        "budgets",
        sa.Column("budget_id", sa.String(length=64), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("period", sa.String(length=32), nullable=False),
        sa.Column("limit_units", sa.BigInteger(), nullable=False),
        sa.Column("spent_units", sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint("budget_id"),
        sa.UniqueConstraint("category"),
    )

    op.create_table(
        "policy_versions",
        sa.Column("policy_version_id", sa.String(length=64), nullable=False),
        sa.Column("doc_id", sa.String(length=128), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("content_hash", sa.String(length=128), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("policy_version_id"),
        sa.UniqueConstraint("content_hash"),
    )
    op.create_index("ix_policy_versions_doc_id", "policy_versions", ["doc_id"])

    op.create_table(
        "agent_runs",
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("request_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("primary_action", sa.String(length=16), nullable=True),
        sa.Column("critic_action", sa.String(length=16), nullable=True),
        sa.Column("final_action", sa.String(length=16), nullable=True),
        sa.Column("timeline", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["request_id"], ["payment_requests.request_id"]),
        sa.PrimaryKeyConstraint("run_id"),
    )
    op.create_index("ix_agent_runs_request_id", "agent_runs", ["request_id"])

    op.create_table(
        "rule_evaluations",
        sa.Column("rule_evaluation_id", sa.String(length=64), nullable=False),
        sa.Column("request_id", sa.String(length=64), nullable=False),
        sa.Column("decision", sa.String(length=16), nullable=False),
        sa.Column("rule_codes", sa.JSON(), nullable=False),
        sa.Column("policy_refs", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["request_id"], ["payment_requests.request_id"]),
        sa.PrimaryKeyConstraint("rule_evaluation_id"),
    )
    op.create_index("ix_rule_evaluations_request_id", "rule_evaluations", ["request_id"])

    op.create_table(
        "keeperhub_executions",
        sa.Column("execution_id", sa.String(length=128), nullable=False),
        sa.Column("request_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("transaction_hash", sa.String(length=66), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(["request_id"], ["payment_requests.request_id"]),
        sa.PrimaryKeyConstraint("execution_id"),
    )
    op.create_index("ix_keeperhub_executions_request_id", "keeperhub_executions", ["request_id"])

    op.create_table(
        "contract_events",
        sa.Column("event_id", sa.String(length=128), nullable=False),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column("transaction_hash", sa.String(length=66), nullable=False),
        sa.Column("event_name", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("event_id"),
    )
    op.create_index("ix_contract_events_request_id", "contract_events", ["request_id"])
    op.create_index("ix_contract_events_transaction_hash", "contract_events", ["transaction_hash"])

    op.create_table(
        "audit_logs",
        sa.Column("audit_id", sa.String(length=64), nullable=False),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column("actor", sa.String(length=64), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("audit_id"),
    )
    op.create_index("ix_audit_logs_request_id", "audit_logs", ["request_id"])


def downgrade() -> None:
    for table_name in [
        "audit_logs",
        "contract_events",
        "keeperhub_executions",
        "rule_evaluations",
        "agent_runs",
        "policy_versions",
        "budgets",
        "approvals",
        "payment_requests",
        "vendor_wallet_history",
        "invoices",
        "vendors",
    ]:
        op.drop_table(table_name)
