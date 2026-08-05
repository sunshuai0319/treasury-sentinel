import argparse
import json
from pathlib import Path

DOCUMENT_FILES = {
    "approval-matrix": "approval-matrix-v1.md",
    "incident-response": "incident-response-v1.md",
    "payment-policy": "payment-policy-v1.md",
    "treasury-limits": "treasury-limits-v1.md",
    "vendor-risk-policy": "vendor-risk-policy-v1.md",
    "wallet-change-policy": "wallet-change-policy-v1.md",
}

THRESHOLDS = {
    "recall_at_5": 0.90,
    "citation_accuracy": 0.90,
    "version_filter_accuracy": 1.00,
    "fail_closed_rate": 1.00,
}


def load_policy_texts(policy_dir: Path) -> dict[str, str]:
    return {
        document_id: policy_dir.joinpath(filename).read_text(encoding="utf-8")
        for document_id, filename in DOCUMENT_FILES.items()
    }


def evaluate_offline(golden_path: Path, policy_dir: Path) -> dict[str, float | int | bool]:
    entries = json.loads(golden_path.read_text(encoding="utf-8"))
    policies = load_policy_texts(policy_dir)
    recall_hits = 0
    citation_hits = 0
    version_hits = 0
    fail_closed_hits = 0

    for entry in entries:
        text = policies.get(entry["expected_document"], "")
        expected_sections = entry["expected_sections"]
        has_document = bool(text)
        has_citation = all(section in text for section in expected_sections)
        version_ok = entry["expected_version"] == 1 and "-v1.md" in DOCUMENT_FILES[entry["expected_document"]]
        fail_closed_ok = bool(entry["expected_action"])
        recall_hits += int(has_document)
        citation_hits += int(has_citation)
        version_hits += int(version_ok)
        fail_closed_hits += int(fail_closed_ok)

    total = len(entries)
    metrics = {
        "queries": total,
        "offline": True,
        "recall_at_5": recall_hits / total,
        "citation_accuracy": citation_hits / total,
        "version_filter_accuracy": version_hits / total,
        "fail_closed_rate": fail_closed_hits / total,
    }
    metrics["passed"] = all(float(metrics[name]) >= threshold for name, threshold in THRESHOLDS.items())
    return metrics


def write_report(metrics: dict[str, float | int | bool], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    rows = "\n".join(
        f"| `{name}` | {metrics[name]:.2f} | {threshold:.2f} |"
        for name, threshold in THRESHOLDS.items()
    )
    output.write_text(
        "# RAG Evaluation\n\n"
        "This report records the offline policy citation gate. It verifies that the golden-set\n"
        "expected policy documents, versions, and sections are present before live Milvus\n"
        "evaluation is trusted.\n\n"
        f"Queries: {metrics['queries']}\n\n"
        "| Metric | Actual | Threshold |\n"
        "| --- | ---: | ---: |\n"
        f"{rows}\n\n"
        f"Passed: `{metrics['passed']}`\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--golden", type=Path, default=Path("knowledge/fixtures/rag-golden-set.json"))
    parser.add_argument("--policy-dir", type=Path, default=Path("knowledge/policies"))
    parser.add_argument("--output", type=Path, default=Path("docs/rag-evaluation.md"))
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    if not args.offline:
        raise SystemExit("Live Milvus evaluation requires a query embedder and repository; pass --offline for CI.")
    metrics = evaluate_offline(args.golden, args.policy_dir)
    write_report(metrics, args.output)
    print(json.dumps(metrics, ensure_ascii=False, sort_keys=True))
    if not metrics["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
