from pathlib import Path

from app.integrations.milvus.embedding import LocalBgeEmbedder

MODEL = Path("/Volumes/wd2t/model/bge-small-zh-v1.5")


def main() -> None:
    assert MODEL.joinpath("model.safetensors").exists() or MODEL.joinpath("pytorch_model.bin").exists()
    embedder = LocalBgeEmbedder(str(MODEL))
    vector = embedder.embed_query("软件供应商 420 USDC 是否可自动付款")
    assert len(vector) == 512
    print({"model": str(MODEL), "dimension": len(vector), "ok": True})


if __name__ == "__main__":
    main()

