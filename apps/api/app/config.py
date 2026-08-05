from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    milvus_uri: str
    milvus_token: str | None = None
    milvus_user: str | None = None
    milvus_password: str | None = None
    milvus_db_name: str | None = None
    milvus_collection: str = "treasury_policy_chunks_bge_zh_v1"
    embedding_model_path: str = "/Volumes/wd2t/model/bge-small-zh-v1.5"
    embedding_dimension: int = 512
    ark_api_key: str
    ark_base_url: str = "https://ark.cn-beijing.volces.com/api/v3"
    doubao_model: str = "doubao-seed-2-0-mini-260428"
    doubao_primary_temperature: float = 0.1
    doubao_critic_temperature: float = 0.1
    doubao_timeout_seconds: float = 60.0
    doubao_primary_max_tokens: int = 192
    doubao_critic_max_tokens: int = 160
    doubao_decision_mode: str = "risk_based"
    keeperhub_api_key: str
    keeperhub_base_url: str = "https://app.keeperhub.com"
    keeperhub_wallet_address: str | None = None
    base_sepolia_rpc_url: str
    chain_id: int = Field(default=84532)
    treasury_guard_address: str | None = None
    demo_usdc_address: str | None = None


def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
