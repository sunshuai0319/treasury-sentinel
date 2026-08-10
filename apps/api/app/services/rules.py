from app.domain.models import Decision, Invoice, RuleResult, Vendor

AUTO_LIMIT_UNITS = 500_000_000


def evaluate_payment(
    vendor: Vendor,
    invoice: Invoice,
    paid_invoice_ids: set[str] | None = None,
    paid_hashes: set[str] | None = None,
) -> RuleResult:
    paid_invoice_ids = paid_invoice_ids or set()
    paid_hashes = paid_hashes or set()
    reasons: list[str] = []
    refs: list[str] = []

    if invoice.invoice_id in paid_invoice_ids or invoice.content_hash in paid_hashes:
        return RuleResult(
            Decision.REJECT,
            ["duplicate invoice or content hash (重复发票或内容哈希)"],
            ["1.1 重复发票"],
            ["DUPLICATE_INVOICE"],
        )
    if invoice.recipient_address.lower() != vendor.wallet_address.lower():
        return RuleResult(
            Decision.REJECT,
            ["recipient address does not match vendor wallet (收款地址与供应商钱包不匹配)"],
            ["2.1 自动付款"],
            ["RECIPIENT_WALLET_MISMATCH"],
        )
    if vendor.wallet_changed_recently:
        return RuleResult(
            Decision.REVIEW,
            ["wallet changed within 24 hours (钱包在24小时内变更)"],
            ["1.1 冷静期"],
            ["WALLET_CHANGE_COOLING_PERIOD"],
        )
    if vendor.status != "APPROVED":
        return RuleResult(
            Decision.REVIEW,
            ["new or unapproved vendor requires finance review (新供应商或未批准供应商需财务复核)"],
            ["1.1 首次付款"],
            ["VENDOR_NOT_APPROVED"],
        )
    if invoice.amount_units > 2_000_000_000:
        return RuleResult(
            Decision.REJECT,
            ["amount requires dual approval outside MVP (金额超出MVP需双级审批)"],
            ["2.3 双级审批"],
            ["AMOUNT_REQUIRES_DUAL_APPROVAL"],
        )
    if invoice.amount_units > AUTO_LIMIT_UNITS:
        return RuleResult(
            Decision.REVIEW,
            ["amount requires finance manager approval (金额需财务经理审批)"],
            ["2.2 单级审批"],
            ["AMOUNT_REQUIRES_FINANCE_REVIEW"],
        )

    reasons.append("approved vendor, matching wallet, unpaid invoice, amount <= 500 USDC (供应商已批准、钱包匹配、发票未支付、金额≤500 USDC)")
    refs.append("2.1 自动付款")
    return RuleResult(Decision.APPROVE, reasons, refs, ["AUTO_PAYMENT_ALLOWED"])
