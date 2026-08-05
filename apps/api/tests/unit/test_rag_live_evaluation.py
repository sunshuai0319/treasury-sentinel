import json
from pathlib import Path

import knowledge.scripts.evaluate_retrieval as eval_mod


def test_live_retrieval_evaluation_uses_embedder_and_repository(monkeypatch, tmp_path: Path):
    golden = tmp_path / "golden.json"
    golden.write_text(
        json.dumps(
            [
                {
                    "query": "软件供应商 420 USDC 是否可自动付款",
                    "expected_document": "payment-policy",
                    "expected_sections": ["2.1"],
                    "expected_version": 1,
                    "expected_action": "APPROVE",
                }
            ]
        ),
        encoding="utf-8",
    )
    env_file = tmp_path / ".env"
    env_file.write_text(
        "DATABASE_URL=sqlite:///tmp.db\n"
        "MILVUS_URI=http://localhost:19530\n"
        "ARK_API_KEY=test\n"
        "KEEPERHUB_API_KEY=test\n"
        "BASE_SEPOLIA_RPC_URL=https://example.invalid\n",
        encoding="utf-8",
    )

    class FakeEmbedder:
        def __init__(self, model_path: str):
            self.model_path = model_path

        def embed_query(self, text: str):
            return [1.0] + [0.0] * 511

    class FakeRepo:
        def __init__(self, *args):
            pass

        def search(self, query_vector, limit=5):
            return [
                {
                    "document_id": "payment-policy",
                    "section_id": "2.1",
                    "policy_version": 1,
                    "content": "2.1 自动付款",
                }
            ]

    monkeypatch.setattr(eval_mod, "LocalBgeEmbedder", FakeEmbedder)
    monkeypatch.setattr(eval_mod, "MilvusPolicyRepository", FakeRepo)

    metrics = eval_mod.evaluate_live(golden, env_file)

    assert metrics["passed"] is True
    assert metrics["offline"] is False
    assert metrics["recall_at_5"] == 1.0
