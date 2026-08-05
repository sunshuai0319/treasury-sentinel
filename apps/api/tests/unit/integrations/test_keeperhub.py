import pytest

from app.integrations.keeperhub import KeeperHubClient


def test_keeperhub_execution_maps_camel_and_snake_case_fields():
    execution = KeeperHubClient._execution_from_json(
        {
            "id": "exec_1",
            "status": "confirmed",
            "transactionHash": "0xabc",
            "errorCode": None,
        }
    )

    assert execution.execution_id == "exec_1"
    assert execution.status == "confirmed"
    assert execution.transaction_hash == "0xabc"


@pytest.mark.asyncio
async def test_keeperhub_contract_call_uses_direct_execution_api(monkeypatch: pytest.MonkeyPatch):
    calls = []

    class FakeResponse:
        def __init__(self, body):
            self.body = body

        def raise_for_status(self):
            return None

        def json(self):
            return self.body

    class FakeAsyncClient:
        def __init__(self, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def post(self, url, json, headers):
            calls.append({"url": url, "json": json, "headers": headers})
            if json.get("simulate"):
                return FakeResponse({"success": True, "status": "simulated", "wouldRevert": False})
            return FakeResponse({"executionId": "direct_123", "status": "submitted"})

    monkeypatch.setattr("app.integrations.keeperhub.httpx.AsyncClient", FakeAsyncClient)

    execution = await KeeperHubClient("kh_test", "https://app.keeperhub.com").execute_contract_call(
        {"contractAddress": "0xabc", "chainId": 84532},
        idempotency_key="pay_123",
    )

    assert execution.execution_id == "direct_123"
    assert [call["url"] for call in calls] == [
        "https://app.keeperhub.com/api/execute/contract-call",
        "https://app.keeperhub.com/api/execute/contract-call",
    ]
    assert calls[0]["json"]["simulate"] is True
    assert "simulate" not in calls[1]["json"]
    assert calls[1]["headers"]["Idempotency-Key"] == "pay_123"
