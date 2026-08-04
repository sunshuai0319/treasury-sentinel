from typing import Literal

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

