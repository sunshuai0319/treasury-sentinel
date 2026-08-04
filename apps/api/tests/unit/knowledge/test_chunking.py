from pathlib import Path

from app.knowledge.chunking import build_policy_chunks, split_policy_document


class FakeEmbedder:
    def embed_documents(self, texts):
        return [[1.0] + [0.0] * 511 for _ in texts]


def test_split_policy_document_extracts_sections():
    text = "# A\n\n## 1.1 One\n\nBody\n\n## 1.2 Two\n\nMore"

    sections = split_policy_document(text)

    assert sections == [("1.1 One", "Body"), ("1.2 Two", "More")]


def test_build_policy_chunks_from_manifest():
    root = Path(__file__).parents[5]

    chunks = build_policy_chunks(root, FakeEmbedder())

    assert len(chunks) == 8
    assert all(len(chunk.embedding) == 512 for chunk in chunks)
    assert {chunk.document_id for chunk in chunks} == {
        "payment-policy",
        "approval-matrix",
        "vendor-risk-policy",
        "treasury-limits",
        "wallet-change-policy",
        "incident-response",
    }

