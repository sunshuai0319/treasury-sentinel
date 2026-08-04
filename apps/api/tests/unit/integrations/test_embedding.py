from app.integrations.milvus.embedding import QUERY_PREFIX, LocalBgeEmbedder


def test_embedder_returns_normalized_512_vector():
    embedder = LocalBgeEmbedder.__new__(LocalBgeEmbedder)
    embedder._encode = lambda texts: [[3.0, 4.0] + [0.0] * 510 for _ in texts]

    result = embedder.embed_documents(["已批准供应商可以付款"])

    assert len(result) == 1
    assert len(result[0]) == 512
    assert round(sum(x * x for x in result[0]), 6) == 1.0


def test_query_uses_bge_prefix():
    seen = {}
    embedder = LocalBgeEmbedder.__new__(LocalBgeEmbedder)

    def fake_encode(texts):
        seen["text"] = texts[0]
        return [[1.0] + [0.0] * 511]

    embedder._encode = fake_encode
    embedder.embed_query("软件供应商 420 USDC 是否可自动付款")

    assert seen["text"].startswith(QUERY_PREFIX)

