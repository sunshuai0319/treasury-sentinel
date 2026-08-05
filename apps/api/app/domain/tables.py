from datetime import datetime

from sqlalchemy import JSON, BigInteger, Boolean, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class VendorTable(Base):
    __tablename__ = "vendors"

    vendor_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32), index=True)
    risk_level: Mapped[str] = mapped_column(String(32))
    category: Mapped[str] = mapped_column(String(32))
    wallet_address: Mapped[str] = mapped_column(String(42))
    wallet_changed_recently: Mapped[bool] = mapped_column(Boolean, default=False)
    max_single_payment_units: Mapped[int] = mapped_column(BigInteger)


class InvoiceTable(Base):
    __tablename__ = "invoices"
    __table_args__ = (UniqueConstraint("content_hash", name="uq_invoices_content_hash"),)

    invoice_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    vendor_id: Mapped[str] = mapped_column(String(32), index=True)
    amount_units: Mapped[int] = mapped_column(BigInteger)
    currency: Mapped[str] = mapped_column(String(16))
    category: Mapped[str] = mapped_column(String(32))
    recipient_address: Mapped[str] = mapped_column(String(42))
    content_hash: Mapped[str] = mapped_column(String(128), index=True)
    status: Mapped[str] = mapped_column(String(32), default="SUBMITTED")


class VendorWalletHistoryTable(Base):
    __tablename__ = "vendor_wallet_history"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    vendor_id: Mapped[str] = mapped_column(String(32), ForeignKey("vendors.vendor_id"), index=True)
    wallet_address: Mapped[str] = mapped_column(String(42))
    changed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    changed_by: Mapped[str] = mapped_column(String(128), default="seed")


class PaymentRequestTable(Base):
    __tablename__ = "payment_requests"
    __table_args__ = (UniqueConstraint("idempotency_key", name="uq_payment_requests_idempotency"),)

    request_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    vendor_id: Mapped[str] = mapped_column(String(32), ForeignKey("vendors.vendor_id"), index=True)
    invoice_id: Mapped[str] = mapped_column(String(64), ForeignKey("invoices.invoice_id"), index=True)
    amount_units: Mapped[int] = mapped_column(BigInteger)
    recipient_address: Mapped[str] = mapped_column(String(42))
    status: Mapped[str] = mapped_column(String(32), default="SUBMITTED", index=True)
    final_action: Mapped[str | None] = mapped_column(String(16), nullable=True)
    decision_hash: Mapped[str | None] = mapped_column(String(66), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ApprovalTable(Base):
    __tablename__ = "approvals"

    approval_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    request_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("payment_requests.request_id"), index=True
    )
    approver: Mapped[str] = mapped_column(String(128))
    decision: Mapped[str] = mapped_column(String(16))
    reason: Mapped[str] = mapped_column(String(512), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class BudgetTable(Base):
    __tablename__ = "budgets"

    budget_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    category: Mapped[str] = mapped_column(String(32), unique=True)
    period: Mapped[str] = mapped_column(String(32))
    limit_units: Mapped[int] = mapped_column(BigInteger)
    spent_units: Mapped[int] = mapped_column(BigInteger, default=0)


class PolicyVersionTable(Base):
    __tablename__ = "policy_versions"

    policy_version_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    doc_id: Mapped[str] = mapped_column(String(128), index=True)
    version: Mapped[str] = mapped_column(String(32))
    content_hash: Mapped[str] = mapped_column(String(128), unique=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class AgentRunTable(Base):
    __tablename__ = "agent_runs"

    run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    request_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("payment_requests.request_id"), index=True
    )
    status: Mapped[str] = mapped_column(String(32), default="STARTED")
    primary_action: Mapped[str | None] = mapped_column(String(16), nullable=True)
    critic_action: Mapped[str | None] = mapped_column(String(16), nullable=True)
    final_action: Mapped[str | None] = mapped_column(String(16), nullable=True)
    timeline: Mapped[dict] = mapped_column(JSON, default=dict)


class RuleEvaluationTable(Base):
    __tablename__ = "rule_evaluations"

    rule_evaluation_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    request_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("payment_requests.request_id"), index=True
    )
    decision: Mapped[str] = mapped_column(String(16))
    rule_codes: Mapped[list] = mapped_column(JSON, default=list)
    policy_refs: Mapped[list] = mapped_column(JSON, default=list)


class KeeperHubExecutionTable(Base):
    __tablename__ = "keeperhub_executions"

    execution_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    request_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("payment_requests.request_id"), index=True
    )
    status: Mapped[str] = mapped_column(String(32), default="PENDING")
    transaction_hash: Mapped[str | None] = mapped_column(String(66), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)


class ContractEventTable(Base):
    __tablename__ = "contract_events"

    event_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    request_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    transaction_hash: Mapped[str] = mapped_column(String(66), index=True)
    event_name: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)


class AuditLogTable(Base):
    __tablename__ = "audit_logs"

    audit_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    request_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    actor: Mapped[str] = mapped_column(String(64))
    action: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
