from collections.abc import Sequence
from math import sqrt
from typing import Any

QUERY_PREFIX = "为这个句子生成表示以用于检索相关文章："


def _normalize(vector: Sequence[float]) -> list[float]:
    length = sqrt(sum(value * value for value in vector))
    if length == 0:
        return [0.0 for _ in vector]
    return [float(value / length) for value in vector]


class LocalBgeEmbedder:
    def __init__(self, model_path: str, device: str | None = None):
        from sentence_transformers import SentenceTransformer

        self.model = SentenceTransformer(model_path, device=device)

    def _encode(self, texts: Sequence[str]) -> list[list[float]]:
        vectors: Any = self.model.encode(
            list(texts),
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return vectors.tolist()

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return [_normalize(vector) for vector in self._encode(texts)]

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([QUERY_PREFIX + text])[0]

