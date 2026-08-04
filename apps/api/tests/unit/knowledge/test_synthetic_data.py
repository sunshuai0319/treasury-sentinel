from knowledge.scripts.generate_synthetic_data import (
    default_output_path,
    generate_dataset,
    golden_set,
)


def test_generator_is_deterministic_and_contains_all_scenarios():
    first = generate_dataset(seed=20260804, vendor_count=40, invoice_count=120)
    second = generate_dataset(seed=20260804, vendor_count=40, invoice_count=120)

    assert first == second
    assert len(first["vendors"]) == 40
    assert len(first["invoices"]) == 120
    assert {x["scenario"] for x in first["invoices"]} == {
        "NORMAL",
        "OVER_LIMIT",
        "DUPLICATE",
        "WALLET_CHANGED",
        "NEW_VENDOR",
        "MISSING_POLICY",
    }


def test_golden_set_covers_documents_and_actions():
    entries = golden_set()

    assert len(entries) == 20
    assert {entry["expected_action"] for entry in entries} == {
        "APPROVE",
        "REVIEW",
        "REJECT",
        "PAUSE",
    }
    assert {entry["expected_document"] for entry in entries} == {
        "payment-policy",
        "approval-matrix",
        "vendor-risk-policy",
        "treasury-limits",
        "wallet-change-policy",
        "incident-response",
    }


def test_default_output_path_is_repo_knowledge_fixtures():
    default = default_output_path()

    assert default.name == "fixtures"
    assert default.parent.name == "knowledge"
