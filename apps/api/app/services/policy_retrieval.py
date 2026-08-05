from collections.abc import Callable
from functools import lru_cache
from typing import Any

from app.config import Settings, get_settings
from app.integrations.milvus.embedding import LocalBgeEmbedder
from app.integrations.milvus.repository import MilvusPolicyRepository

PolicyRetriever = Callable[[str], list[dict[str, Any]]]


@lru_cache(maxsize=1)
def get_live_policy_retriever() -> PolicyRetriever:
    def retrieve(query: str) -> list[dict[str, Any]]:
        return _search_live_policy(query)

    return retrieve


@lru_cache(maxsize=1)
def _live_components() -> tuple[LocalBgeEmbedder, MilvusPolicyRepository]:
    settings = get_settings()
    embedder = LocalBgeEmbedder(settings.embedding_model_path)
    repository = MilvusPolicyRepository(
        settings.milvus_uri,
        settings.milvus_token,
        settings.milvus_collection,
        settings.embedding_dimension,
        settings.milvus_user,
        settings.milvus_password,
        settings.milvus_db_name,
    )
    return embedder, repository


def _search_live_policy(query: str) -> list[dict[str, Any]]:
    embedder, repository = _live_components()
    return repository.search(embedder.embed_query(query), limit=5)


def build_live_policy_retriever(settings: Settings) -> PolicyRetriever:
    embedder = LocalBgeEmbedder(settings.embedding_model_path)
    repository = MilvusPolicyRepository(
        settings.milvus_uri,
        settings.milvus_token,
        settings.milvus_collection,
        settings.embedding_dimension,
        settings.milvus_user,
        settings.milvus_password,
        settings.milvus_db_name,
    )
    return lambda query: repository.search(embedder.embed_query(query), limit=5)
