import json

from app.config import Settings
from app.integrations.milvus.repository import MilvusPolicyRepository


def main() -> None:
    settings = Settings()  # type: ignore[call-arg]
    repo = MilvusPolicyRepository(
        settings.milvus_uri,
        settings.milvus_token,
        settings.milvus_collection,
        settings.embedding_dimension,
        settings.milvus_user,
        settings.milvus_password,
        settings.milvus_db_name,
    )
    kwargs = repo.connection_kwargs()
    masked = {
        "uri": kwargs.get("uri"),
        "user": kwargs.get("user"),
        "password_set": bool(kwargs.get("password")),
        "password_len": len(kwargs.get("password") or ""),
        "token_set": bool(kwargs.get("token")),
        "db_name": kwargs.get("db_name") or "default",
        "collection": settings.milvus_collection,
    }
    try:
        collections = repo.client().list_collections()
        print(json.dumps({"connected": True, "auth": masked, "collections": collections}, ensure_ascii=False))
    except Exception as exc:
        print(
            json.dumps(
                {
                    "connected": False,
                    "auth": masked,
                    "error_type": type(exc).__name__,
                    "error": str(exc).split("\n")[0],
                },
                ensure_ascii=False,
            )
        )
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
