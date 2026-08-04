import argparse
import json
from pathlib import Path

from app.config import Settings
from app.integrations.milvus.embedding import LocalBgeEmbedder
from app.integrations.milvus.repository import MilvusPolicyRepository
from app.knowledge.chunking import build_policy_chunks


class ZeroEmbedder:
    def embed_documents(self, texts):
        return [[1.0] + [0.0] * 511 for _ in texts]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).parents[2])
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.dry_run:
        embedder = ZeroEmbedder()
        chunks = build_policy_chunks(args.root, embedder)
        print(json.dumps({"chunks": len(chunks), "dry_run": True}, ensure_ascii=False))
        return

    settings = Settings()  # type: ignore[call-arg]
    embedder = LocalBgeEmbedder(settings.embedding_model_path)
    chunks = build_policy_chunks(args.root, embedder)
    repo = MilvusPolicyRepository(
        settings.milvus_uri,
        settings.milvus_token,
        settings.milvus_collection,
        settings.embedding_dimension,
    )
    inserted = repo.upsert_chunks(chunks)
    print(json.dumps({"chunks": inserted, "collection": settings.milvus_collection}))


if __name__ == "__main__":
    main()

