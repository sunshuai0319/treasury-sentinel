from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal, cast
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.agent.graph import TreasuryAgentGraph
from app.agent.state import PaymentRun
from app.domain.models import Invoice, Vendor
from app.domain.tables import (
    AgentRunTable,
    ApprovalTable,
    AuditLogTable,
    KeeperHubExecutionTable,
    PaymentRequestTable,
    RuleEvaluationTable,
    VendorTable,
)
from app.services.decision_hash import stable_decision_hash
from app.services.rules import evaluate_payment


@dataclass(frozen=True)
class PaymentRequestRecord:
    request_id: str
    idempotency_key: str
    vendor_id: str
    invoice_id: str
    amount_units: int
    recipient_address: str
    status: str
    final_action: str | None
    decision_hash: str | None
    keeperhub_execution_id: str | None
    transaction_hash: str | None


def record_from_table(row: PaymentRequestTable) -> PaymentRequestRecord:
    return PaymentRequestRecord(
        request_id=row.request_id,
        idempotency_key=row.idempotency_key,
        vendor_id=row.vendor_id,
        invoice_id=row.invoice_id,
        amount_units=row.amount_units,
        recipient_address=row.recipient_address,
        status=row.status,
        final_action=row.final_action,
        decision_hash=row.decision_hash,
        keeperhub_execution_id=row.keeperhub_execution_id,
        transaction_hash=row.transaction_hash,
    )


class PaymentWorkflowRepository:
    def __init__(self, session_factory: Callable[[], Session]):
        self.session_factory = session_factory

    def create(
        self,
        *,
        idempotency_key: str,
        vendor_id: str,
        invoice_id: str,
        amount_units: int,
        recipient_address: str,
    ) -> PaymentRequestRecord:
        with self.session_factory() as session:
            existing = self._get_by_idempotency(session, idempotency_key)
            if existing:
                return record_from_table(existing)

            row = PaymentRequestTable(
                request_id=f"pay_{uuid4().hex[:12]}",
                idempotency_key=idempotency_key,
                vendor_id=vendor_id,
                invoice_id=invoice_id,
                amount_units=amount_units,
                recipient_address=recipient_address,
            )
            session.add(row)
            self._audit(session, row.request_id, "api", "payment_request.created", {})
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                existing = self._get_by_idempotency(session, idempotency_key)
                if existing:
                    return record_from_table(existing)
                raise
            return record_from_table(row)

    def get(self, request_id: str) -> PaymentRequestRecord | None:
        with self.session_factory() as session:
            row = session.get(PaymentRequestTable, request_id)
            return record_from_table(row) if row else None

    def analyze(self, request_id: str) -> PaymentRun | None:
        with self.session_factory() as session:
            row = session.get(PaymentRequestTable, request_id)
            if not row:
                return None

            vendor_row = session.get(VendorTable, row.vendor_id)
            vendor = Vendor(
                vendor_id=row.vendor_id,
                status=vendor_row.status if vendor_row else "APPROVED",
                wallet_address=vendor_row.wallet_address if vendor_row else row.recipient_address,
                category=vendor_row.category if vendor_row else "software",
                max_single_payment_units=vendor_row.max_single_payment_units if vendor_row else 500_000_000,
                wallet_changed_recently=vendor_row.wallet_changed_recently if vendor_row else False,
            )
            invoice = Invoice(
                invoice_id=row.invoice_id,
                vendor_id=row.vendor_id,
                amount_units=row.amount_units,
                currency="USDC",
                category=vendor.category,
                recipient_address=row.recipient_address,
                content_hash=stable_decision_hash({"invoice_id": row.invoice_id}),
            )
            graph_run = TreasuryAgentGraph().run(
                {
                    "request_id": row.request_id,
                    "scenario": "workflow",
                    "invoice_id": invoice.invoice_id,
                    "vendor_id": vendor.vendor_id,
                    "amount_units": invoice.amount_units,
                    "vendor_status": vendor.status,
                    "vendor_wallet": vendor.wallet_address,
                    "recipient_address": invoice.recipient_address,
                    "category": invoice.category,
                    "wallet_changed_recently": vendor.wallet_changed_recently,
                }
            )
            rule = evaluate_payment(vendor, invoice)
            final_action = cast(Literal["APPROVE", "REVIEW", "REJECT", "PAUSE"], graph_run.final_action)
            timeline = graph_run.timeline
            row.final_action = final_action
            row.status = "APPROVED" if final_action == "APPROVE" else final_action
            row.decision_hash = stable_decision_hash(
                {
                    "request_id": row.request_id,
                    "invoice_id": row.invoice_id,
                    "final_action": row.final_action,
                    "rule_codes": rule.rule_codes,
                    "policy_refs": rule.policy_refs,
                }
            )
            session.merge(
                RuleEvaluationTable(
                    rule_evaluation_id=f"rule_{uuid4().hex[:12]}",
                    request_id=row.request_id,
                    decision=final_action,
                    rule_codes=rule.rule_codes,
                    policy_refs=rule.policy_refs,
                )
            )
            session.merge(
                AgentRunTable(
                    run_id=f"run_{uuid4().hex[:12]}",
                    request_id=row.request_id,
                    status="COMPLETED",
                    primary_action=timeline[0].action,
                    critic_action=timeline[1].action,
                    final_action=timeline[2].action,
                    timeline=[item.model_dump() for item in timeline],
                )
            )
            self._audit(session, row.request_id, "agent", "payment_request.analyzed", {"decision": final_action})
            session.commit()
            return PaymentRun(
                request_id=row.request_id,
                scenario="workflow",
                invoice_id=row.invoice_id,
                vendor_id=row.vendor_id,
                final_action=final_action,
                timeline=timeline,
                keeperhub_execution_id=row.keeperhub_execution_id,
                transaction_hash=row.transaction_hash,
            )

    def approve(self, request_id: str, approver: str, reason: str) -> PaymentRequestRecord | None:
        with self.session_factory() as session:
            row = session.get(PaymentRequestTable, request_id)
            if not row:
                return None
            row.status = "APPROVED"
            row.final_action = "APPROVE"
            if not row.decision_hash:
                row.decision_hash = stable_decision_hash({"request_id": row.request_id, "approval": "manual"})
            session.add(
                ApprovalTable(
                    approval_id=f"appr_{uuid4().hex[:12]}",
                    request_id=row.request_id,
                    approver=approver,
                    decision="APPROVE",
                    reason=reason,
                )
            )
            self._audit(session, row.request_id, approver, "payment_request.approved", {"reason": reason})
            session.commit()
            return record_from_table(row)

    def mark_execution_blocked(self, request_id: str, reason: str) -> PaymentRequestRecord | None:
        with self.session_factory() as session:
            row = session.get(PaymentRequestTable, request_id)
            if not row:
                return None
            row.status = "EXECUTION_BLOCKED"
            self._audit(session, row.request_id, "api", "payment_request.execution_blocked", {"reason": reason})
            session.commit()
            return record_from_table(row)

    def mark_confirming(self, request_id: str) -> PaymentRequestRecord | None:
        with self.session_factory() as session:
            row = session.get(PaymentRequestTable, request_id)
            if not row:
                return None
            row.status = "CONFIRMING"
            self._audit(session, row.request_id, "keeperhub", "payment_request.confirming", {})
            session.commit()
            return record_from_table(row)

    def list_recoverable(self) -> list[PaymentRequestRecord]:
        with self.session_factory() as session:
            rows = session.scalars(
                select(PaymentRequestTable).where(
                    PaymentRequestTable.status.in_(["SIMULATING", "EXECUTING", "CONFIRMING"])
                )
            ).all()
            return [record_from_table(row) for row in rows]

    def timeline_events(self, request_id: str) -> list[dict]:
        with self.session_factory() as session:
            runs = session.scalars(
                select(AgentRunTable)
                .where(AgentRunTable.request_id == request_id)
                .order_by(AgentRunTable.run_id)
            ).all()
            events: list[dict] = []
            for run in runs:
                for index, item in enumerate(run.timeline or []):
                    events.append(
                        {
                            "id": f"{run.run_id}:{index}",
                            "event": item.get("actor", "agent"),
                            "data": item,
                        }
                    )
            row = session.get(PaymentRequestTable, request_id)
            if row:
                events.append(
                    {
                        "id": f"{request_id}:status",
                        "event": "status",
                        "data": {
                            "request_id": row.request_id,
                            "status": row.status,
                            "decision_hash": row.decision_hash,
                            "keeperhub_execution_id": row.keeperhub_execution_id,
                            "transaction_hash": row.transaction_hash,
                        },
                    }
                )
            return events

    def update_execution_status(
        self,
        *,
        request_id: str,
        execution_id: str,
        status: str,
        transaction_hash: str | None,
        error_code: str | None,
    ) -> PaymentRequestRecord | None:
        normalized_status = status.upper()
        with self.session_factory() as session:
            row = session.get(PaymentRequestTable, request_id)
            if not row:
                return None
            session.merge(
                KeeperHubExecutionTable(
                    execution_id=execution_id,
                    request_id=request_id,
                    status=normalized_status,
                    transaction_hash=transaction_hash,
                    error_code=error_code,
                )
            )
            row.keeperhub_execution_id = execution_id
            row.transaction_hash = transaction_hash
            if normalized_status in {"CONFIRMED", "SUCCESS", "SUCCEEDED"}:
                row.status = "CONFIRMED"
            elif normalized_status in {"FAILED", "CANCELLED", "REVERTED"}:
                row.status = "FAILED"
            else:
                row.status = "CONFIRMING"
            self._audit(
                session,
                row.request_id,
                "keeperhub",
                "payment_request.execution_status_updated",
                {"execution_id": execution_id, "status": normalized_status},
            )
            session.commit()
            return record_from_table(row)

    @staticmethod
    def _get_by_idempotency(session: Session, key: str) -> PaymentRequestTable | None:
        return session.scalar(select(PaymentRequestTable).where(PaymentRequestTable.idempotency_key == key))

    @staticmethod
    def _audit(session: Session, request_id: str, actor: str, action: str, payload: dict) -> None:
        session.add(
            AuditLogTable(
                audit_id=f"audit_{uuid4().hex[:12]}",
                request_id=request_id,
                actor=actor,
                action=action,
                payload=payload,
            )
        )
