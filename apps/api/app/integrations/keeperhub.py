from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(frozen=True)
class KeeperHubExecution:
    execution_id: str
    status: str
    transaction_hash: str | None = None
    error_code: str | None = None


class KeeperHubClient:
    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"}

    async def read_prechecks(self) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(f"{self.base_url}/prechecks", headers=self._headers())
            response.raise_for_status()
            return response.json()

    async def simulate_payment(self, payload: dict[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self.base_url}/simulations", json=payload, headers=self._headers()
            )
            response.raise_for_status()
            return response.json()

    async def execute_contract_call(self, payload: dict[str, Any]) -> KeeperHubExecution:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{self.base_url}/executions", json=payload, headers=self._headers()
            )
            response.raise_for_status()
            return self._execution_from_json(response.json())

    async def get_status(self, execution_id: str) -> KeeperHubExecution:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(
                f"{self.base_url}/executions/{execution_id}", headers=self._headers()
            )
            response.raise_for_status()
            return self._execution_from_json(response.json())

    async def pause_treasury(self, payload: dict[str, Any]) -> KeeperHubExecution:
        return await self.execute_contract_call(payload)

    @staticmethod
    def _execution_from_json(data: dict[str, Any]) -> KeeperHubExecution:
        return KeeperHubExecution(
            execution_id=str(data.get("id") or data.get("execution_id")),
            status=str(data.get("status", "submitted")),
            transaction_hash=data.get("transactionHash") or data.get("transaction_hash"),
            error_code=data.get("errorCode") or data.get("error_code"),
        )
