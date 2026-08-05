from app.agent.state import AgentDecision, PaymentRun
from app.domain.models import Decision, Invoice, Vendor
from app.services.rules import evaluate_payment

DEMO_VENDOR = Vendor(
    vendor_id="V001",
    status="APPROVED",
    wallet_address="0x0000000000000000000000000000000000000001",
    category="SOFTWARE",
    max_single_payment_units=500_000_000,
)

DEMO_INVOICE = Invoice(
    invoice_id="INV-2026-DEMO",
    vendor_id="V001",
    amount_units=420_000_000,
    currency="USDC",
    category="SOFTWARE",
    recipient_address="0x0000000000000000000000000000000000000001",
    content_hash="hash-demo",
)


def scenario_inputs(scenario: str) -> tuple[Vendor, Invoice, set[str]]:
    if scenario == "duplicate":
        return DEMO_VENDOR, DEMO_INVOICE, {"INV-2026-DEMO"}
    if scenario == "wallet_changed":
        return DEMO_VENDOR.__class__(**{**DEMO_VENDOR.__dict__, "wallet_changed_recently": True}), DEMO_INVOICE, set()
    if scenario == "over_limit":
        invoice = DEMO_INVOICE.__class__(**{**DEMO_INVOICE.__dict__, "amount_units": 700_000_000})
        return DEMO_VENDOR, invoice, set()
    if scenario == "address_mismatch":
        invoice = DEMO_INVOICE.__class__(
            **{
                **DEMO_INVOICE.__dict__,
                "recipient_address": "0x0000000000000000000000000000000000009999",
            }
        )
        return DEMO_VENDOR, invoice, set()
    if scenario == "pause":
        invoice = DEMO_INVOICE.__class__(
            **{
                **DEMO_INVOICE.__dict__,
                "recipient_address": "0x0000000000000000000000000000000000009999",
            }
        )
        return DEMO_VENDOR, invoice, set()
    return DEMO_VENDOR, DEMO_INVOICE, set()


def run_demo_scenario(scenario: str) -> PaymentRun:
    vendor, invoice, paid_ids = scenario_inputs(scenario)
    rule = evaluate_payment(vendor, invoice, paid_invoice_ids=paid_ids)
    final = Decision.PAUSE if scenario == "pause" else rule.decision
    timeline = [
        AgentDecision(
            actor="primary",
            action=rule.decision.value,
            confidence=0.82,
            reasons=rule.reasons,
            policy_refs=rule.policy_refs,
        ),
        AgentDecision(
            actor="critic",
            action=final.value,
            confidence=0.9,
            reasons=["critic checked deterministic rules and policy citations"],
            policy_refs=rule.policy_refs,
        ),
        AgentDecision(
            actor="final",
            action=final.value,
            confidence=1.0,
            reasons=rule.reasons if final != Decision.PAUSE else ["address anomaly threshold reached"],
            policy_refs=rule.policy_refs if final != Decision.PAUSE else ["1.1 地址异常"],
        ),
    ]
    return PaymentRun(
        request_id=f"demo-{scenario}",
        scenario=scenario,
        invoice_id=invoice.invoice_id,
        vendor_id=vendor.vendor_id,
        final_action=final.value,
        timeline=timeline,
    )
