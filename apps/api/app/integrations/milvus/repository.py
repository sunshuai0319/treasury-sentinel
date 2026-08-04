from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from pymilvus import Collection, connections, utility

from app.integrations.milvus.schema import POLICY_INDEX_PARAMS, policy_collection_schema


@dataclass(frozen=True)
class PolicyChunk:
    chunk_id: str
    document_id: str
    policy_version: int
    section_id: str
    title: str
    content: str
    document_type: str
    payment_category: str
    approval_level: str
    effective_from: int
    effective_to: int
    content_hash: str
    embedding: list[float]


class MilvusPolicyRepository:
    def __init__(
        self,
        uri: str,
        token: str | None,
        collection_name: str,
        dimension: int = 512,
        user: str | None = None,
        password: str | None = None,
    ):
        self.uri = uri
        self.token = token
        self.user = user
        self.password = password
        self.collection_name = collection_name
        self.dimension = dimension
        self.alias = "treasury_sentinel"

    def connect(self) -> None:
        kwargs: dict[str, Any] = {"alias": self.alias, "uri": self.uri}
        if self.user and self.password:
            kwargs["user"] = self.user
            kwargs["password"] = self.password
        elif self.token:
            kwargs["token"] = self.token
        connections.connect(**kwargs)

    def ensure_collection(self) -> Collection:
        self.connect()
        if not utility.has_collection(self.collection_name, using=self.alias):
            collection = Collection(
                self.collection_name,
                schema=policy_collection_schema(self.dimension),
                using=self.alias,
            )
            collection.create_index("embedding", POLICY_INDEX_PARAMS)
        else:
            collection = Collection(self.collection_name, using=self.alias)
        collection.load()
        return collection

    def upsert_chunks(self, chunks: Sequence[PolicyChunk]) -> int:
        if not chunks:
            return 0
        collection = self.ensure_collection()
        collection.upsert([chunk.__dict__ for chunk in chunks])
        collection.flush()
        return len(chunks)

    def delete_document_version(self, document_id: str, policy_version: int) -> None:
        collection = self.ensure_collection()
        collection.delete(f'document_id == "{document_id}" and policy_version == {policy_version}')
        collection.flush()

    def search(self, query_vector: list[float], limit: int = 5) -> list[dict[str, Any]]:
        collection = self.ensure_collection()
        fields = [
            "chunk_id",
            "document_id",
            "policy_version",
            "section_id",
            "title",
            "content",
            "document_type",
            "content_hash",
        ]
        results = collection.search(
            [query_vector],
            "embedding",
            {"metric_type": "COSINE", "params": {}},
            limit=limit,
            output_fields=fields,
        )
        return [
            {"score": hit.score, **{field: hit.entity.get(field) for field in fields}}
            for hit in results[0]
        ]
