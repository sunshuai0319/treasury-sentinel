from dataclasses import dataclass, field
from typing import Literal, cast
from uuid import uuid4

from app.agent.state import AgentDecision, PaymentRun
from app.domain.models import Invoice, Vendor
from app.services.decision_hash import stable_decision_hash
from app.services.rules import evaluate_payment


@dataclass
class PaymentRequestRecord:
    request_id: str
    idempotency_key: str
    vendor_id: str
    invoice_id: str
    amount_units: int
    recipient_address: str
    status: str = "SUBMITTED"
    final_action: str | None = None
    decision_hash: str | None = None
    keeperhub_execution_id: str | None = None
    transaction_hash: str | None = None
    timeline: list[AgentDecision] = field(default_factory=list)


class PaymentWorkflowStore:
    def __init__(self) -> None:
        self._by_idempotency: dict[str, PaymentRequestRecord] = {}
        self._by_request_id: dict[str, PaymentRequestRecord] = {}

    def create(
        self,
        *,
        idempotency_key: str,
        vendor_id: str,
        invoice_id: str,
        amount_units: int,
        recipient_address: str,
    ) -> PaymentRequestRecord:
        existing = self._by_idempotency.get(idempotency_key)
        if existing:
            return existing

        record = PaymentRequestRecord(
            request_id=f"pay_{uuid4().hex[:12]}",
            idempotency_key=idempotency_key,
            vendor_id=vendor_id,
            invoice_id=invoice_id,
            amount_units=amount_units,
            recipient_address=recipient_address,
        )
        self._by_idempotency[idempotency_key] = record
        self._by_request_id[record.request_id] = record
        return record

    def get(self, request_id: str) -> PaymentRequestRecord | None:
        return self._by_request_id.get(request_id)

    def analyze(self, record: PaymentRequestRecord) -> PaymentRun:
        vendor = Vendor(
            vendor_id=record.vendor_id,
            status="APPROVED",
            wallet_address=record.recipient_address,
            category="software",
            max_single_payment_units=500_000_000,
        )
        invoice = Invoice(
            invoice_id=record.invoice_id,
            vendor_id=record.vendor_id,
            amount_units=record.amount_units,
            currency="USDC",
            category="software",
            recipient_address=record.recipient_address,
            content_hash=stable_decision_hash({"invoice_id": record.invoice_id}),
        )
        rule = evaluate_payment(vendor, invoice)
        primary = AgentDecision(
            actor="primary",
            action=rule.decision.value,
            confidence=0.82,
            reasons=rule.reasons,
            policy_refs=rule.policy_refs,
        )
        critic_action = (
            "REVIEW" if rule.decision.value == "APPROVE" and record.amount_units > 0 else rule.decision.value
        )
        final_action = cast(Literal["APPROVE", "REVIEW", "REJECT", "PAUSE"], rule.decision.value)
        critic = AgentDecision(
            actor="critic",
            action=cast(Literal["APPROVE", "REVIEW", "REJECT", "PAUSE"], critic_action),
            confidence=0.76,
            reasons=[*rule.reasons, f"rule_codes={','.join(rule.rule_codes)}"],
            policy_refs=rule.policy_refs,
        )
        final = AgentDecision(
            actor="final",
            action=final_action,
            confidence=0.9,
            reasons=rule.reasons,
            policy_refs=rule.policy_refs,
        )
        record.timeline = [primary, critic, final]
        record.final_action = final_action
        record.status = "APPROVED" if rule.decision.value == "APPROVE" else rule.decision.value
        record.decision_hash = stable_decision_hash(
            {
                "request_id": record.request_id,
                "invoice_id": record.invoice_id,
                "final_action": record.final_action,
                "rule_codes": rule.rule_codes,
                "policy_refs": rule.policy_refs,
            }
        )
        return PaymentRun(
            request_id=record.request_id,
            scenario="workflow",
            invoice_id=record.invoice_id,
            vendor_id=record.vendor_id,
            final_action=final_action,
            timeline=record.timeline,
            keeperhub_execution_id=record.keeperhub_execution_id,
            transaction_hash=record.transaction_hash,
        )


store = PaymentWorkflowStore()
