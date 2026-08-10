from dataclasses import dataclass
from typing import Any

import httpx

SUCCESS_STATUSES = {"COMPLETED", "CONFIRMED", "SUCCESS", "SUCCEEDED"}
TERMINAL_FAILURE_STATUSES = {"FAILED", "CANCELLED", "CANCELED", "REVERTED", "REJECTED"}
TERMINAL_ERROR_CODES = {"INVALID_PARAMS", "PERMISSION_DENIED", "UNAUTHORIZED", "FORBIDDEN"}


def classify_execution_status(status: str, error_code: str | None = None) -> str:
    normalized_status = status.upper()
    normalized_error = error_code.upper() if error_code else None
    if normalized_status in SUCCESS_STATUSES:
        return "SUCCESS"
    if normalized_status in TERMINAL_FAILURE_STATUSES or normalized_error in TERMINAL_ERROR_CODES:
        return "TERMINAL"
    return "RETRYABLE"


@dataclass(frozen=True)
class KeeperHubExecution:
    execution_id: str
    status: str
    transaction_hash: str | None = None
    error_code: str | None = None
    category: str = "RETRYABLE"


class KeeperHubClient:
    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"}

    def _headers_with_idempotency(self, idempotency_key: str | None = None) -> dict[str, str]:
        headers = self._headers()
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        return headers

    async def read_prechecks(self) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(f"{self.base_url}/api/chains", headers=self._headers())
            response.raise_for_status()
            return response.json()

    async def simulate_payment(self, payload: dict[str, Any]) -> dict[str, Any]:
        simulation_payload = {**payload, "simulate": True}
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self.base_url}/api/execute/contract-call",
                json=simulation_payload,
                headers=self._headers(),
            )
            response.raise_for_status()
            return response.json()

    async def execute_contract_call(
        self, payload: dict[str, Any], idempotency_key: str | None = None
    ) -> KeeperHubExecution:
        await self.simulate_payment(payload)
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{self.base_url}/api/execute/contract-call",
                json=payload,
                headers=self._headers_with_idempotency(idempotency_key),
            )
            response.raise_for_status()
            return self._execution_from_json(response.json())

    async def execute_payment(
        self, payload: dict[str, Any], idempotency_key: str | None = None
    ) -> KeeperHubExecution:
        return await self.execute_contract_call(payload, idempotency_key=idempotency_key)

    async def get_status(self, execution_id: str) -> KeeperHubExecution:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(
                f"{self.base_url}/api/execute/{execution_id}/status", headers=self._headers()
            )
            response.raise_for_status()
            return self._execution_from_json(response.json())

    async def pause_treasury(self, payload: dict[str, Any]) -> KeeperHubExecution:
        return await self.execute_contract_call(payload)

    @staticmethod
    def _execution_from_json(data: dict[str, Any]) -> KeeperHubExecution:
        status = str(data.get("status", "submitted"))
        error_code = data.get("errorCode") or data.get("error_code")
        return KeeperHubExecution(
            execution_id=str(data.get("executionId") or data.get("id") or data.get("execution_id")),
            status=status,
            transaction_hash=data.get("transactionHash") or data.get("transaction_hash") or data.get("txHash"),
            error_code=error_code,
            category=classify_execution_status(status, error_code),
        )
