from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from pymilvus import MilvusClient

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
        db_name: str | None = None,
    ):
        self.uri = uri
        self.token = token
        self.user = user
        self.password = password
        self.db_name = db_name
        self.collection_name = collection_name
        self.dimension = dimension
        self._client: MilvusClient | None = None

    def connection_kwargs(self) -> dict[str, Any]:
        kwargs: dict[str, Any] = {"uri": self.uri}
        if self.user and self.password:
            kwargs["user"] = self.user
            kwargs["password"] = self.password
        elif self.token:
            kwargs["token"] = self.token
        if self.db_name:
            kwargs["db_name"] = self.db_name
        return kwargs

    def client(self) -> MilvusClient:
        if self._client is None:
            self._client = MilvusClient(**self.connection_kwargs())
        return self._client

    def ensure_collection(self) -> None:
        client = self.client()
        if not client.has_collection(self.collection_name):
            index_params = MilvusClient.prepare_index_params()
            index_params.add_index(field_name="embedding", **POLICY_INDEX_PARAMS)
            client.create_collection(
                self.collection_name,
                schema=policy_collection_schema(self.dimension),
                index_params=index_params,
            )
        client.load_collection(self.collection_name)

    def upsert_chunks(self, chunks: Sequence[PolicyChunk]) -> int:
        if not chunks:
            return 0
        self.ensure_collection()
        client = self.client()
        client.upsert(self.collection_name, [chunk.__dict__ for chunk in chunks])
        client.flush(self.collection_name)
        return len(chunks)

    def delete_document_version(self, document_id: str, policy_version: int) -> None:
        self.ensure_collection()
        client = self.client()
        client.delete(
            self.collection_name,
            filter=f'document_id == "{document_id}" and policy_version == {policy_version}',
        )
        client.flush(self.collection_name)

    def search(self, query_vector: list[float], limit: int = 5) -> list[dict[str, Any]]:
        self.ensure_collection()
        client = self.client()
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
        results = client.search(
            self.collection_name,
            data=[query_vector],
            anns_field="embedding",
            search_params={"metric_type": "COSINE", "params": {}},
            limit=limit,
            output_fields=fields,
        )
        return [{"score": hit["distance"], **hit.get("entity", {})} for hit in results[0]]
