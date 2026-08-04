from pathlib import Path


def test_env_examples_are_owned_by_each_workspace():
    root = Path(__file__).parents[4]

    assert not root.joinpath(".env.example").exists()
    assert root.joinpath("apps/api/.env.example").exists()
    assert root.joinpath("apps/web/.env.example").exists()
    assert root.joinpath("contracts/.env.example").exists()


def test_env_examples_do_not_mix_frontend_and_backend_public_config():
    root = Path(__file__).parents[4]
    api_env = root.joinpath("apps/api/.env.example").read_text()
    web_env = root.joinpath("apps/web/.env.example").read_text()
    contract_env = root.joinpath("contracts/.env.example").read_text()

    assert "DATABASE_URL=" in api_env
    assert "KEEPERHUB_API_KEY=" in api_env
    assert "NEXT_PUBLIC_API_BASE_URL=" not in api_env

    assert web_env.strip() == "NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api"
    assert "DEPLOYER_PRIVATE_KEY=" in contract_env
    assert "DATABASE_URL=" not in contract_env

