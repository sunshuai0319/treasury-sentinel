import asyncio
import json
import os

from app.config import Settings
from app.integrations.keeperhub import KeeperHubClient


async def main() -> None:
    settings = Settings()  # type: ignore[call-arg]
    required = [
        "KEEPERHUB_API_KEY",
        "TREASURY_GUARD_ADDRESS",
        "DEMO_USDC_ADDRESS",
        "KEEPERHUB_WALLET_ADDRESS",
    ]
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        raise SystemExit(f"Missing live execution env vars: {', '.join(missing)}")

    client = KeeperHubClient(settings.keeperhub_api_key, settings.keeperhub_base_url)
    payload = {
        "chainId": settings.chain_id,
        "contractAddress": settings.treasury_guard_address,
        "description": "Treasury Sentinel live smoke payload. Adjust ABI/method for KeeperHub API shape.",
        "dryRunRecommended": True,
    }
    result = await client.execute_contract_call(payload)
    print(json.dumps(result.__dict__, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())

