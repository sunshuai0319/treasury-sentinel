from dataclasses import dataclass
from enum import StrEnum


class Decision(StrEnum):
    APPROVE = "APPROVE"
    REVIEW = "REVIEW"
    REJECT = "REJECT"
    PAUSE = "PAUSE"


@dataclass(frozen=True)
class Vendor:
    vendor_id: str
    status: str
    wallet_address: str
    category: str
    max_single_payment_units: int
    wallet_changed_recently: bool = False


@dataclass(frozen=True)
class Invoice:
    invoice_id: str
    vendor_id: str
    amount_units: int
    currency: str
    category: str
    recipient_address: str
    content_hash: str


@dataclass(frozen=True)
class RuleResult:
    decision: Decision
    reasons: list[str]
    policy_refs: list[str]
    rule_codes: list[str]
