from app.config import Settings


def test_settings_accept_local_embedding_path():
    settings = Settings(
        database_url="postgresql+psycopg://u:p@localhost/db",
        milvus_uri="http://localhost:19530",
        embedding_model_path="/Volumes/wd2t/model/bge-small-zh-v1.5",
        ark_api_key="test",
        keeperhub_api_key="test",
        base_sepolia_rpc_url="https://example.invalid",
        chain_id=84532,
    )

    assert settings.embedding_dimension == 512
    assert settings.doubao_model == "doubao-seed-2-1-pro-260628"
    assert settings.chain_id == 84532


def test_settings_accept_milvus_user_password():
    settings = Settings(
        database_url="postgresql+psycopg://u:p@localhost/db",
        milvus_uri="http://localhost:19530",
        milvus_user="root",
        milvus_password="milvus",
        ark_api_key="test",
        keeperhub_api_key="test",
        base_sepolia_rpc_url="https://example.invalid",
    )

    assert settings.milvus_user == "root"
    assert settings.milvus_password == "milvus"
