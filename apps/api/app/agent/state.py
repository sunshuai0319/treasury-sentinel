from typing import Literal, TypedDict

from pydantic import BaseModel


class AgentDecision(BaseModel):
    actor: Literal["primary", "critic", "final"]
    action: Literal["APPROVE", "REVIEW", "REJECT", "PAUSE"]
    confidence: float
    reasons: list[str]
    policy_refs: list[str]


class PaymentRun(BaseModel):
    request_id: str
    scenario: str
    invoice_id: str
    vendor_id: str
    final_action: Literal["APPROVE", "REVIEW", "REJECT", "PAUSE"]
    timeline: list[AgentDecision]
    keeperhub_execution_id: str | None = None
    transaction_hash: str | None = None


class PolicyEvidence(BaseModel):
    document_id: str
    section_id: str
    title: str
    content: str
    score: float | None = None


class AgentGraphState(TypedDict, total=False):
    request_id: str
    scenario: str
    invoice_id: str
    vendor_id: str
    amount_units: int
    vendor_status: str
    vendor_wallet: str
    recipient_address: str
    category: str
    wallet_changed_recently: bool
    paid_invoice_ids: set[str]
    policy_evidence: list[dict]
    timeline: list[dict]
    final_action: Literal["APPROVE", "REVIEW", "REJECT", "PAUSE"]
    rule_codes: list[str]
    error: str | None
