from app.integrations.milvus.repository import MilvusPolicyRepository


def test_connection_kwargs_prefers_user_password_over_token():
    repo = MilvusPolicyRepository(
        uri="http://localhost:19530",
        token="token-value",
        collection_name="policies",
        user="root",
        password="secret",
        db_name="default",
    )

    assert repo.connection_kwargs() == {
        "uri": "http://localhost:19530",
        "user": "root",
        "password": "secret",
        "db_name": "default",
    }


def test_connection_kwargs_supports_token_auth():
    repo = MilvusPolicyRepository(
        uri="http://localhost:19530",
        token="token-value",
        collection_name="policies",
    )

    assert repo.connection_kwargs() == {
        "uri": "http://localhost:19530",
        "token": "token-value",
    }
