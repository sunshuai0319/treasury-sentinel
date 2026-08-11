from collections.abc import Iterator

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api import routes
from app.config import Settings
from app.db import Base
from app.domain.tables import InvoiceTable, VendorTable
from app.integrations.doubao import CriticDecision, PrimaryDecision
from app.integrations.keeperhub import KeeperHubExecution
from app.main import app
from app.services.payment_workflow import PaymentWorkflowRepository


class FakeLlmDecisionProvider:
    def primary(self, state, policy_refs):
        return PrimaryDecision(
            action="AUTO_EXECUTE",
            risk_score=20,
            reasons=["test primary approves with policy evidence"],
            citation_ids=["payment-policy#2.1 自动付款"],
        )

    def critic(self, state, primary, policy_refs):
        return CriticDecision(
            challenge=False,
            blocking_issues=[],
            recommended_action="AUTO_EXECUTE",
        )


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(engine)
    with SessionLocal() as session:
        seed_business_rows(session)
    routes.get_repository.cache_clear()
    routes.get_keeperhub_client.cache_clear()
    app.dependency_overrides = {}
    monkeypatch.setattr(routes, "get_repository", lambda: PaymentWorkflowRepository(SessionLocal))
    monkeypatch.setattr(
        routes,
        "get_live_policy_retriever",
        lambda: lambda _: [
            {
                "document_id": "payment-policy",
                "section_id": "2.1 自动付款",
                "policy_version": 1,
                "score": 0.92,
            }
        ],
    )
    monkeypatch.setattr(routes, "get_live_llm_decision_provider", lambda: FakeLlmDecisionProvider())
    monkeypatch.setattr(
        routes,
        "get_settings",
        lambda: Settings(
            database_url="sqlite+pysqlite:///:memory:",
            milvus_uri="http://localhost:19530",
            ark_api_key="test",
            keeperhub_api_key="",
            base_sepolia_rpc_url="https://example.invalid",
        ),
    )
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides = {}


def seed_business_rows(session: Session) -> None:
    session.add_all(
        [
            VendorTable(
                vendor_id="vendor_demo",
                name="Demo Vendor",
                status="APPROVED",
                risk_level="LOW",
                category="software",
                wallet_address="0x1111111111111111111111111111111111111111",
                wallet_changed_recently=False,
                max_single_payment_units=500_000_000,
            ),
            InvoiceTable(
                invoice_id="inv_demo_001",
                vendor_id="vendor_demo",
                amount_units=420_000_000,
                currency="USDC",
                category="software",
                recipient_address="0x1111111111111111111111111111111111111111",
                content_hash="hash_001",
            ),
            InvoiceTable(
                invoice_id="inv_demo_002",
                vendor_id="vendor_demo",
                amount_units=700_000_000,
                currency="USDC",
                category="software",
                recipient_address="0x2222222222222222222222222222222222222222",
                content_hash="hash_002",
            ),
        ]
    )
    session.commit()


def test_payment_request_is_idempotent_and_analyzable(client: TestClient):
    payload = {
        "vendor_id": "vendor_demo",
        "invoice_id": "inv_demo_001",
        "amount_units": 420_000_000,
        "recipient_address": "0x1111111111111111111111111111111111111111",
    }
    first = client.post("/api/payment-requests", json=payload, headers={"Idempotency-Key": "idem-1"})
    second = client.post("/api/payment-requests", json=payload, headers={"Idempotency-Key": "idem-1"})

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["request_id"] == second.json()["request_id"]

    fetched = client.get(f"/api/payment-requests/{first.json()['request_id']}")
    assert fetched.status_code == 200

    analyzed = client.post(f"/api/payment-requests/{first.json()['request_id']}/analyze?sync=true")
    assert analyzed.status_code == 200
    assert analyzed.json()["final_action"] == "APPROVE"

    audit = client.get(f"/api/payment-requests/{first.json()['request_id']}/audit")
    assert audit.status_code == 200
    assert audit.json()["decision_hash"].startswith("0x")


def test_analyze_defaults_to_async_and_exposes_progress_events(client: TestClient):
    payload = {
        "vendor_id": "vendor_demo",
        "invoice_id": "inv_demo_001",
        "amount_units": 420_000_000,
        "recipient_address": "0x1111111111111111111111111111111111111111",
    }
    created = client.post("/api/payment-requests", json=payload, headers={"Idempotency-Key": "idem-async"})
    request_id = created.json()["request_id"]

    started = client.post(f"/api/payment-requests/{request_id}/analyze")

    assert started.status_code == 202
    assert started.json()["status"] in {"ANALYZING", "APPROVED"}
    events = client.get(f"/api/payment-requests/{request_id}/events")
    assert events.status_code == 200
    assert "event: status" in events.text


def test_analyze_accepts_idempotency_key_and_does_not_restart_completed_analysis(client: TestClient):
    payload = {
        "vendor_id": "vendor_demo",
        "invoice_id": "inv_demo_001",
        "amount_units": 420_000_000,
        "recipient_address": "0x1111111111111111111111111111111111111111",
    }
    created = client.post("/api/payment-requests", json=payload, headers={"Idempotency-Key": "idem-analyze"})
    request_id = created.json()["request_id"]

    first = client.post(
        f"/api/payment-requests/{request_id}/analyze",
        headers={"Idempotency-Key": "analysis-idem-1"},
    )
    second = client.post(
        f"/api/payment-requests/{request_id}/analyze",
        headers={"Idempotency-Key": "analysis-idem-1"},
    )

    assert first.status_code in {200, 202}
    assert second.status_code == 200
    assert second.json()["request_id"] == request_id
    assert second.json()["status"] == "APPROVED"


def test_review_payment_can_be_manually_approved_then_fail_closed_on_execute(client: TestClient):
    payload = {
        "vendor_id": "vendor_demo",
        "invoice_id": "inv_demo_002",
        "amount_units": 700_000_000,
        "recipient_address": "0x2222222222222222222222222222222222222222",
    }
    created = client.post("/api/payment-requests", json=payload, headers={"Idempotency-Key": "idem-2"})
    request_id = created.json()["request_id"]

    analyzed = client.post(f"/api/payment-requests/{request_id}/analyze?sync=true")
    assert analyzed.json()["final_action"] == "REJECT"

    approved = client.post(
        f"/api/payment-requests/{request_id}/approve",
        json={"approver": "finance@example.com", "reason": "manual test approval"},
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "APPROVED"

    executed = client.post(f"/api/payment-requests/{request_id}/execute")
    assert executed.status_code == 503


def test_approved_payment_executes_through_keeperhub(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    captured_payloads = []
    captured_idempotency_keys = []

    class FakeKeeperHubClient:
        async def execute_payment(self, payload, idempotency_key=None):
            captured_payloads.append(payload)
            captured_idempotency_keys.append(idempotency_key)
            return KeeperHubExecution(
                execution_id="exec_test_123",
                status="submitted",
                transaction_hash="0xabc",
            )

    payload = {
        "vendor_id": "vendor_demo",
        "invoice_id": "inv_demo_001",
        "amount_units": 420_000_000,
        "recipient_address": "0x1111111111111111111111111111111111111111",
    }
    created = client.post("/api/payment-requests", json=payload, headers={"Idempotency-Key": "idem-exec"})
    request_id = created.json()["request_id"]
    # analyze 在无 keeperhub 配置下运行:判定 APPROVE 但保持 APPROVED,不自动上链
    client.post(f"/api/payment-requests/{request_id}/analyze?sync=true")

    # 补齐配置后,通过手动 execute 端点触发上链(保留手动路径语义)
    monkeypatch.setattr(routes, "get_settings", lambda: _configured_settings())
    monkeypatch.setattr(routes, "get_keeperhub_client", lambda: FakeKeeperHubClient())
    executed = client.post(f"/api/payment-requests/{request_id}/execute", headers={"Idempotency-Key": "exec-idem-1"})

    assert executed.status_code == 200
    body = executed.json()
    assert body["status"] == "CONFIRMING"
    assert body["keeperhub_execution_id"] == "exec_test_123"
    assert body["transaction_hash"] == "0xabc"
    assert captured_payloads[0]["contractAddress"] == "0xcC615A47EFC313172376341Edd5DAfD0f79f8EB3"
    assert captured_payloads[0]["functionName"] == "executePaymentWithExpiry"
    assert captured_payloads[0]["arguments"]["amount"] == "420000000"
    assert captured_idempotency_keys == ["exec-idem-1"]


def test_legacy_confirming_without_execution_id_can_retry_keeperhub_execution(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    class FakeKeeperHubClient:
        async def execute_payment(self, payload, idempotency_key=None):
            return KeeperHubExecution(execution_id="exec_retry_123", status="submitted")

    payload = {
        "vendor_id": "vendor_demo",
        "invoice_id": "inv_demo_001",
        "amount_units": 420_000_000,
        "recipient_address": "0x1111111111111111111111111111111111111111",
    }
    created = client.post("/api/payment-requests", json=payload, headers={"Idempotency-Key": "idem-retry"})
    request_id = created.json()["request_id"]
    client.post(f"/api/payment-requests/{request_id}/analyze?sync=true")
    # 模拟 legacy 数据:CONFIRMING 但无 execution_id
    routes.get_repository().mark_confirming(request_id)

    monkeypatch.setattr(routes, "get_settings", lambda: _configured_settings())
    monkeypatch.setattr(routes, "get_keeperhub_client", lambda: FakeKeeperHubClient())
    executed = client.post(f"/api/payment-requests/{request_id}/execute")

    assert executed.status_code == 200
    assert executed.json()["keeperhub_execution_id"] == "exec_retry_123"


def test_execution_blocked_without_execution_id_can_retry_after_configuration_fix(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    class FakeKeeperHubClient:
        async def execute_payment(self, payload, idempotency_key=None):
            return KeeperHubExecution(execution_id="exec_unblocked_123", status="submitted")

    payload = {
        "vendor_id": "vendor_demo",
        "invoice_id": "inv_demo_001",
        "amount_units": 420_000_000,
        "recipient_address": "0x1111111111111111111111111111111111111111",
    }
    created = client.post("/api/payment-requests", json=payload, headers={"Idempotency-Key": "idem-blocked"})
    request_id = created.json()["request_id"]
    client.post(f"/api/payment-requests/{request_id}/analyze?sync=true")
    failed = client.post(f"/api/payment-requests/{request_id}/execute")
    assert failed.status_code == 503

    monkeypatch.setattr(
        routes,
        "get_settings",
        lambda: Settings(
            database_url="sqlite+pysqlite:///:memory:",
            milvus_uri="http://localhost:19530",
            ark_api_key="test",
            keeperhub_api_key="kh_test",
            keeperhub_wallet_address="0x7836A8deB72B27F94d0dF555E23d684aDC894Fe6",
            treasury_guard_address="0xcC615A47EFC313172376341Edd5DAfD0f79f8EB3",
            demo_usdc_address="0x8eEf98476B371BF01D99CBCEA4D7745B49040c95",
            base_sepolia_rpc_url="https://example.invalid",
        ),
    )
    monkeypatch.setattr(routes, "get_keeperhub_client", lambda: FakeKeeperHubClient())

    retried = client.post(f"/api/payment-requests/{request_id}/execute")

    assert retried.status_code == 200
    assert retried.json()["keeperhub_execution_id"] == "exec_unblocked_123"


def test_recoverable_endpoint_returns_confirming_records(client: TestClient):
    payload = {
        "vendor_id": "vendor_demo",
        "invoice_id": "inv_demo_001",
        "amount_units": 420_000_000,
        "recipient_address": "0x1111111111111111111111111111111111111111",
    }
    created = client.post("/api/payment-requests", json=payload, headers={"Idempotency-Key": "idem-3"})
    request_id = created.json()["request_id"]
    client.post(f"/api/payment-requests/{request_id}/analyze?sync=true")

    repo = routes.get_repository()
    repo.mark_confirming(request_id)

    recoverable = client.get("/api/execution/recoverable")
    assert recoverable.status_code == 200
    assert [item["request_id"] for item in recoverable.json()] == [request_id]


def test_sse_events_stream_agent_timeline(client: TestClient):
    payload = {
        "vendor_id": "vendor_demo",
        "invoice_id": "inv_demo_001",
        "amount_units": 420_000_000,
        "recipient_address": "0x1111111111111111111111111111111111111111",
    }
    created = client.post("/api/payment-requests", json=payload, headers={"Idempotency-Key": "idem-4"})
    request_id = created.json()["request_id"]
    client.post(f"/api/payment-requests/{request_id}/analyze?sync=true")

    events = client.get(f"/api/payment-requests/{request_id}/events")
    assert events.status_code == 200
    assert "event: primary" in events.text
    assert "event: critic" in events.text
    assert "event: final" in events.text
    assert "event: status" in events.text

    first_event_id = next(line.removeprefix("id: ") for line in events.text.splitlines() if line.startswith("id: "))
    resumed = client.get(f"/api/payment-requests/{request_id}/events?last_event_id={first_event_id}")
    assert resumed.status_code == 200
    assert f"id: {first_event_id}" not in resumed.text


def test_review_payment_can_be_rejected_via_api(client: TestClient):
    payload = {
        "vendor_id": "vendor_demo",
        "invoice_id": "inv_demo_over_limit",
        "amount_units": 700_000_000,
        "recipient_address": "0x1111111111111111111111111111111111111111",
    }
    created = client.post("/api/payment-requests", json=payload, headers={"Idempotency-Key": "idem-reject"})
    request_id = created.json()["request_id"]

    analyzed = client.post(f"/api/payment-requests/{request_id}/analyze?sync=true")
    assert analyzed.json()["final_action"] == "REVIEW"

    rejected = client.post(
        f"/api/payment-requests/{request_id}/reject",
        json={"approver": "finance@example.com", "reason": "policy escalation declined"},
    )
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "REJECT"
    assert rejected.json()["final_action"] == "REJECT"


def test_list_payment_requests_filters_by_status(client: TestClient):
    approved_payload = {
        "vendor_id": "vendor_demo",
        "invoice_id": "inv_demo_001",
        "amount_units": 420_000_000,
        "recipient_address": "0x1111111111111111111111111111111111111111",
    }
    approved = client.post(
        "/api/payment-requests", json=approved_payload, headers={"Idempotency-Key": "idem-list-approved"}
    )
    client.post(f"/api/payment-requests/{approved.json()['request_id']}/analyze?sync=true")

    review_payload = {
        "vendor_id": "vendor_demo",
        "invoice_id": "inv_demo_over_limit",
        "amount_units": 700_000_000,
        "recipient_address": "0x1111111111111111111111111111111111111111",
    }
    review = client.post("/api/payment-requests", json=review_payload, headers={"Idempotency-Key": "idem-list-review"})
    review_id = review.json()["request_id"]
    client.post(f"/api/payment-requests/{review_id}/analyze?sync=true")

    review_list = client.get("/api/payment-requests?status=REVIEW")
    assert review_list.status_code == 200
    ids = [item["request_id"] for item in review_list.json()]
    assert review_id in ids
    assert approved.json()["request_id"] not in ids

    all_list = client.get("/api/payment-requests")
    assert all_list.status_code == 200
    assert review_id in [item["request_id"] for item in all_list.json()]


def _configured_settings() -> Settings:
    return Settings(
        database_url="sqlite+pysqlite:///:memory:",
        milvus_uri="http://localhost:19530",
        ark_api_key="test",
        keeperhub_api_key="kh_test",
        keeperhub_wallet_address="0x7836A8deB72B27F94d0dF555E23d684aDC894Fe6",
        treasury_guard_address="0xcC615A47EFC313172376341Edd5DAfD0f79f8EB3",
        demo_usdc_address="0x8eEf98476B371BF01D99CBCEA4D7745B49040c95",
        base_sepolia_rpc_url="https://example.invalid",
    )


def _payment_payload() -> dict:
    return {
        "vendor_id": "vendor_demo",
        "invoice_id": "inv_demo_001",
        "amount_units": 420_000_000,
        "recipient_address": "0x1111111111111111111111111111111111111111",
    }


def test_analyze_approve_auto_executes_when_configured(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    captured_payloads = []

    class FakeKeeperHubClient:
        async def execute_payment(self, payload, idempotency_key=None):
            captured_payloads.append(payload)
            return KeeperHubExecution(
                execution_id="exec_auto_123",
                status="submitted",
                transaction_hash="0xauto",
            )

    monkeypatch.setattr(routes, "get_keeperhub_client", lambda: FakeKeeperHubClient())
    monkeypatch.setattr(routes, "get_settings", lambda: _configured_settings())
    created = client.post(
        "/api/payment-requests", json=_payment_payload(), headers={"Idempotency-Key": "idem-auto-exec"}
    )
    request_id = created.json()["request_id"]

    analyzed = client.post(f"/api/payment-requests/{request_id}/analyze?sync=true")

    assert analyzed.json()["final_action"] == "APPROVE"
    assert captured_payloads, "expected automatic keeperhub execution after approve"
    final = client.get(f"/api/payment-requests/{request_id}").json()
    assert final["keeperhub_execution_id"] == "exec_auto_123"
    assert final["transaction_hash"] == "0xauto"
    assert final["status"] in {"CONFIRMING", "CONFIRMED"}
    assert captured_payloads[0]["functionName"] == "executePaymentWithExpiry"


def _review_payment_payload() -> dict:
    return {
        "vendor_id": "vendor_demo",
        "invoice_id": "inv_demo_over_limit",
        "amount_units": 700_000_000,
        "recipient_address": "0x1111111111111111111111111111111111111111",
    }


def test_manual_approve_auto_executes_when_configured(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    captured_payloads = []

    class FakeKeeperHubClient:
        async def execute_payment(self, payload, idempotency_key=None):
            captured_payloads.append(payload)
            return KeeperHubExecution(
                execution_id="exec_appr_1",
                status="submitted",
                transaction_hash="0xappr",
            )

    monkeypatch.setattr(routes, "get_keeperhub_client", lambda: FakeKeeperHubClient())
    monkeypatch.setattr(routes, "get_settings", lambda: _configured_settings())
    created = client.post(
        "/api/payment-requests", json=_review_payment_payload(), headers={"Idempotency-Key": "idem-appr"}
    )
    request_id = created.json()["request_id"]
    analyzed = client.post(f"/api/payment-requests/{request_id}/analyze?sync=true")
    assert analyzed.json()["final_action"] == "REVIEW"

    approved = client.post(
        f"/api/payment-requests/{request_id}/approve",
        json={"approver": "finance@example.com", "reason": "review approved"},
    )

    assert approved.status_code == 200
    assert captured_payloads, "expected automatic keeperhub execution after manual approval"
    final = client.get(f"/api/payment-requests/{request_id}").json()
    assert final["keeperhub_execution_id"] == "exec_appr_1"
    assert final["transaction_hash"] == "0xappr"
    assert final["status"] in {"CONFIRMING", "CONFIRMED"}


def test_auto_execute_failure_marks_execution_blocked(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    class FailingKeeperHubClient:
        async def execute_payment(self, payload, idempotency_key=None):
            raise httpx.HTTPStatusError(
                "rejected",
                request=httpx.Request("POST", "https://app.keeperhub.com/api/execute/contract-call"),
                response=httpx.Response(502),
            )

    monkeypatch.setattr(routes, "get_keeperhub_client", lambda: FailingKeeperHubClient())
    monkeypatch.setattr(routes, "get_settings", lambda: _configured_settings())
    created = client.post(
        "/api/payment-requests", json=_payment_payload(), headers={"Idempotency-Key": "idem-blocked-auto"}
    )
    request_id = created.json()["request_id"]
    client.post(f"/api/payment-requests/{request_id}/analyze?sync=true")

    final = client.get(f"/api/payment-requests/{request_id}").json()
    assert final["status"] == "EXECUTION_BLOCKED"
    assert final["keeperhub_execution_id"] is None


def test_auto_execute_does_not_double_broadcast(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    captured_payloads = []

    class FakeKeeperHubClient:
        async def execute_payment(self, payload, idempotency_key=None):
            captured_payloads.append(payload)
            return KeeperHubExecution(
                execution_id="exec_once",
                status="submitted",
                transaction_hash="0xonce",
            )

    monkeypatch.setattr(routes, "get_keeperhub_client", lambda: FakeKeeperHubClient())
    monkeypatch.setattr(routes, "get_settings", lambda: _configured_settings())
    created = client.post(
        "/api/payment-requests", json=_payment_payload(), headers={"Idempotency-Key": "idem-once"}
    )
    request_id = created.json()["request_id"]
    client.post(f"/api/payment-requests/{request_id}/analyze?sync=true")
    assert len(captured_payloads) == 1

    executed = client.post(f"/api/payment-requests/{request_id}/execute")
    assert executed.status_code == 409
    assert len(captured_payloads) == 1


def test_analyze_does_not_rewind_already_executed_request(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    captured_payloads = []

    class FakeKeeperHubClient:
        async def execute_payment(self, payload, idempotency_key=None):
            captured_payloads.append(payload)
            return KeeperHubExecution(
                execution_id="exec_no_rewind",
                status="submitted",
                transaction_hash="0xrewind",
            )

    monkeypatch.setattr(routes, "get_keeperhub_client", lambda: FakeKeeperHubClient())
    monkeypatch.setattr(routes, "get_settings", lambda: _configured_settings())
    created = client.post(
        "/api/payment-requests", json=_payment_payload(), headers={"Idempotency-Key": "idem-no-rewind"}
    )
    request_id = created.json()["request_id"]
    client.post(f"/api/payment-requests/{request_id}/analyze?sync=true")
    assert client.get(f"/api/payment-requests/{request_id}").json()["status"] == "CONFIRMING"

    # 对已执行的请求再次分析(不带 idempotency-key),不应把状态倒退成 APPROVED 或重新广播
    client.post(f"/api/payment-requests/{request_id}/analyze?sync=true")

    final = client.get(f"/api/payment-requests/{request_id}").json()
    assert final["status"] == "CONFIRMING"
    assert final["keeperhub_execution_id"] == "exec_no_rewind"
    assert len(captured_payloads) == 1


def test_analyze_rejects_duplicate_invoice_already_paid(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    class FakeKeeperHubClient:
        async def execute_payment(self, payload, idempotency_key=None):
            return KeeperHubExecution(
                execution_id="exec_dup_a",
                status="completed",
                transaction_hash="0xdupa",
            )

    monkeypatch.setattr(routes, "get_keeperhub_client", lambda: FakeKeeperHubClient())
    monkeypatch.setattr(routes, "get_settings", lambda: _configured_settings())

    # 请求 A:inv_demo_001 → 自动执行 → CONFIRMED(链上已付)
    created_a = client.post(
        "/api/payment-requests", json=_payment_payload(), headers={"Idempotency-Key": "idem-dup-a"}
    )
    rid_a = created_a.json()["request_id"]
    client.post(f"/api/payment-requests/{rid_a}/analyze?sync=true")
    assert client.get(f"/api/payment-requests/{rid_a}").json()["status"] == "CONFIRMED"

    # 请求 B:同 invoice_id → analyze 应判 REJECT(重复发票),不自动执行
    created_b = client.post(
        "/api/payment-requests", json=_payment_payload(), headers={"Idempotency-Key": "idem-dup-b"}
    )
    rid_b = created_b.json()["request_id"]
    analyzed_b = client.post(f"/api/payment-requests/{rid_b}/analyze?sync=true")
    assert analyzed_b.json()["final_action"] == "REJECT"
    final_b = client.get(f"/api/payment-requests/{rid_b}").json()
    assert final_b["status"] == "REJECT"
    assert final_b["keeperhub_execution_id"] is None
