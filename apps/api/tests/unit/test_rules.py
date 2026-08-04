from app.domain.models import Decision, Invoice, Vendor
from app.services.rules import evaluate_payment


def vendor(**overrides):
    data = {
        "vendor_id": "V001",
        "status": "APPROVED",
        "wallet_address": "0x0000000000000000000000000000000000000001",
        "category": "SOFTWARE",
        "max_single_payment_units": 500_000_000,
        "wallet_changed_recently": False,
    }
    data.update(overrides)
    return Vendor(**data)


def invoice(**overrides):
    data = {
        "invoice_id": "INV-1",
        "vendor_id": "V001",
        "amount_units": 420_000_000,
        "currency": "USDC",
        "category": "SOFTWARE",
        "recipient_address": "0x0000000000000000000000000000000000000001",
        "content_hash": "hash-1",
    }
    data.update(overrides)
    return Invoice(**data)


def test_low_risk_payment_is_approved():
    result = evaluate_payment(vendor(), invoice())

    assert result.decision == Decision.APPROVE
    assert "2.1 自动付款" in result.policy_refs


def test_duplicate_invoice_is_rejected():
    result = evaluate_payment(vendor(), invoice(), paid_invoice_ids={"INV-1"})

    assert result.decision == Decision.REJECT
    assert "1.1 重复发票" in result.policy_refs


def test_wallet_change_requires_review():
    result = evaluate_payment(vendor(wallet_changed_recently=True), invoice())

    assert result.decision == Decision.REVIEW
    assert "1.1 冷静期" in result.policy_refs

