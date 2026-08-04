import argparse
import json
import random
from pathlib import Path
from typing import Any

SCENARIOS = (
    ["NORMAL"] * 45
    + ["OVER_LIMIT"] * 15
    + ["DUPLICATE"] * 10
    + ["WALLET_CHANGED"] * 15
    + ["NEW_VENDOR"] * 10
    + ["MISSING_POLICY"] * 5
)

CATEGORIES = ("SOFTWARE", "MARKETING", "OPERATIONS")
RISK_LEVELS = ("LOW", "MEDIUM", "HIGH")


def generate_dataset(seed: int, vendor_count: int, invoice_count: int) -> dict[str, Any]:
    rng = random.Random(seed)
    vendors = []
    for i in range(1, vendor_count + 1):
        vendors.append(
            {
                "vendor_id": f"V{i:03d}",
                "name": f"Demo Vendor {i:03d}",
                "status": "NEW" if i % 10 == 0 else "APPROVED",
                "risk_level": RISK_LEVELS[i % len(RISK_LEVELS)],
                "category": CATEGORIES[i % len(CATEGORIES)],
                "wallet_address": "0x" + f"{i:040x}",
                "wallet_changed_at": "2026-08-04T08:00:00Z" if i % 7 == 0 else None,
                "allowed_currency": ["USDC"],
                "max_single_payment_units": 500_000_000,
            }
        )

    invoices = []
    used_hashes: list[str] = []
    for i in range(invoice_count):
        scenario = SCENARIOS[i % len(SCENARIOS)]
        vendor = rng.choice(vendors)
        source = i - 1 if scenario == "DUPLICATE" and i else i
        amount = 700_000_000 if scenario == "OVER_LIMIT" else rng.randint(50, 450) * 1_000_000
        if scenario == "NEW_VENDOR":
            vendor = next(item for item in vendors if item["status"] == "NEW")
        if scenario == "WALLET_CHANGED":
            vendor = next(item for item in vendors if item["wallet_changed_at"])
        content_hash = f"hash-{source:04d}"
        if scenario == "DUPLICATE" and used_hashes:
            content_hash = used_hashes[-1]
        used_hashes.append(content_hash)
        recipient = vendor["wallet_address"]
        if scenario == "MISSING_POLICY":
            recipient = "0x" + f"{9999 + i:040x}"
        invoices.append(
            {
                "invoice_id": f"INV-2026-{source:04d}",
                "vendor_id": vendor["vendor_id"],
                "amount_units": amount,
                "currency": "USDC",
                "category": vendor["category"],
                "scenario": scenario,
                "content_hash": content_hash,
                "recipient_address": recipient,
                "description": f"{scenario.lower()} demo invoice {i:03d}",
                "issued_at": "2026-08-04T00:00:00Z",
            }
        )
    return {"seed": seed, "vendors": vendors, "invoices": invoices}


def golden_set() -> list[dict[str, Any]]:
    entries = [
        ("已批准供应商 420 USDC 是否可以自动付款", "payment-policy", ["2.1 自动付款"], "APPROVE"),
        ("600 USDC 软件订阅付款需要什么审批", "payment-policy", ["2.2 单级审批"], "REVIEW"),
        ("2500 USDC 付款 MVP 是否执行", "payment-policy", ["2.3 双级审批"], "REJECT"),
        ("新供应商首次付款能否自动执行", "approval-matrix", ["1.1 首次付款"], "REVIEW"),
        ("重复发票应该如何处理", "vendor-risk-policy", ["1.1 重复发票"], "REJECT"),
        ("相同内容哈希的发票可以重新付款吗", "vendor-risk-policy", ["1.1 重复发票"], "REJECT"),
        ("软件预算能否借用市场营销预算", "treasury-limits", ["1.1 分类预算"], "REJECT"),
        ("分类预算不足时 Agent 应该怎么做", "treasury-limits", ["1.1 分类预算"], "REJECT"),
        ("钱包地址刚变更还能自动付款吗", "wallet-change-policy", ["1.1 冷静期"], "REVIEW"),
        ("24 小时冷静期内地址匹配是否可以自动付款", "wallet-change-policy", ["1.1 冷静期"], "REVIEW"),
        ("一小时三次地址异常后需要什么动作", "incident-response", ["1.1 地址异常"], "PAUSE"),
        ("暂停建议需要记录哪些内容", "incident-response", ["1.1 地址异常"], "PAUSE"),
        ("低风险供应商小额付款需要哪些条件", "payment-policy", ["2.1 自动付款"], "APPROVE"),
        ("财务经理审批后能否重新检查链上执行", "payment-policy", ["2.2 单级审批"], "REVIEW"),
        ("负责人和财务经理都需要审批的是哪类金额", "payment-policy", ["2.3 双级审批"], "REJECT"),
        ("供应商 PENDING_REVIEW 是否视为首次付款", "approval-matrix", ["1.1 首次付款"], "REVIEW"),
        ("原付款无效前重复发票能否人工降级", "vendor-risk-policy", ["1.1 重复发票"], "REJECT"),
        ("市场营销预算和软件订阅预算是否独立", "treasury-limits", ["1.1 分类预算"], "REJECT"),
        ("当前白名单地址一致但刚修改过钱包如何处理", "wallet-change-policy", ["1.1 冷静期"], "REVIEW"),
        ("地址异常暂停建议要包含触发请求吗", "incident-response", ["1.1 地址异常"], "PAUSE"),
    ]
    return [
        {
            "query": query,
            "expected_document": document,
            "expected_version": 1,
            "expected_sections": sections,
            "expected_action": action,
            "required_conditions": ["policy_version=1", "cite_required_section"],
        }
        for query, document, sections, action in entries
    ]


def write_dataset(output: Path, seed: int = 20260804) -> None:
    output.mkdir(parents=True, exist_ok=True)
    data = generate_dataset(seed, 40, 120)
    (output / "vendors.seed.json").write_text(
        json.dumps(data["vendors"], ensure_ascii=False, indent=2) + "\n"
    )
    (output / "invoices.seed.json").write_text(
        json.dumps(data["invoices"], ensure_ascii=False, indent=2) + "\n"
    )
    (output / "rag-golden-set.json").write_text(
        json.dumps(golden_set(), ensure_ascii=False, indent=2) + "\n"
    )


def default_output_path() -> Path:
    return Path(__file__).parents[1] / "fixtures"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=20260804)
    parser.add_argument("--output", type=Path, default=default_output_path())
    args = parser.parse_args()
    write_dataset(args.output, args.seed)


if __name__ == "__main__":
    main()
