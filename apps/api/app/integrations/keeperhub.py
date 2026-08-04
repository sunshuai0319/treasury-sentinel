from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(frozen=True)
class KeeperHubExecution:
    execution_id: str
    status: str
    transaction_hash: str | None = None


class KeeperHubClient:
    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    async def execute_contract_call(self, payload: dict[str, Any]) -> KeeperHubExecution:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(f"{self.base_url}/executions", json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
        return KeeperHubExecution(
            execution_id=data.get("id") or data.get("execution_id"),
            status=data.get("status", "submitted"),
            transaction_hash=data.get("transaction_hash"),
        )

