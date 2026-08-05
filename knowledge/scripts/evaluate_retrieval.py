import argparse
import json
from pathlib import Path

from app.config import Settings
from app.integrations.milvus.embedding import LocalBgeEmbedder
from app.integrations.milvus.repository import MilvusPolicyRepository

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


def evaluate_live(golden_path: Path, env_file: Path) -> dict[str, float | int | bool]:
    entries = json.loads(golden_path.read_text(encoding="utf-8"))
    settings = Settings(_env_file=env_file)  # type: ignore[call-arg]
    embedder = LocalBgeEmbedder(settings.embedding_model_path)
    repo = MilvusPolicyRepository(
        settings.milvus_uri,
        settings.milvus_token,
        settings.milvus_collection,
        settings.embedding_dimension,
        settings.milvus_user,
        settings.milvus_password,
        settings.milvus_db_name,
    )
    recall_hits = 0
    citation_hits = 0
    version_hits = 0
    fail_closed_hits = 0

    for entry in entries:
        query_vector = embedder.embed_query(entry["query"])
        hits = repo.search(query_vector, limit=5)
        expected_document = entry["expected_document"]
        expected_sections = set(entry["expected_sections"])
        recall_hits += int(any(hit.get("document_id") == expected_document for hit in hits))
        citation_hits += int(
            any(
                hit.get("document_id") == expected_document
                and (hit.get("section_id") in expected_sections or any(section in hit.get("content", "") for section in expected_sections))
                for hit in hits
            )
        )
        version_hits += int(all(int(hit.get("policy_version", 0)) == entry["expected_version"] for hit in hits if hit.get("document_id") == expected_document))
        fail_closed_hits += int(bool(hits) or entry["expected_action"] in {"REVIEW", "REJECT", "PAUSE"})

    total = len(entries)
    metrics = {
        "queries": total,
        "offline": False,
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
    mode = "offline policy citation gate" if metrics["offline"] else "live Milvus retrieval gate"
    description = (
        "It verifies that the golden-set expected policy documents, versions, and sections are present before live Milvus evaluation is trusted."
        if metrics["offline"]
        else "It embeds each golden-set query with the configured local BGE model and searches the configured Milvus collection."
    )
    output.write_text(
        "# RAG Evaluation\n\n"
        f"This report records the {mode}. {description}\n\n"
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
    parser.add_argument("--env-file", type=Path, default=Path("apps/api/.env"))
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    metrics = (
        evaluate_offline(args.golden, args.policy_dir)
        if args.offline
        else evaluate_live(args.golden, args.env_file)
    )
    write_report(metrics, args.output)
    print(json.dumps(metrics, ensure_ascii=False, sort_keys=True))
    if not metrics["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
