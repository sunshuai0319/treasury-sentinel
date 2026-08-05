from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api import routes
from app.db import Base
from app.domain.tables import InvoiceTable, VendorTable
from app.main import app
from app.services.payment_workflow import PaymentWorkflowRepository


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
    app.dependency_overrides = {}
    monkeypatch.setattr(routes, "get_repository", lambda: PaymentWorkflowRepository(SessionLocal))
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

    analyzed = client.post(f"/api/payment-requests/{first.json()['request_id']}/analyze")
    assert analyzed.status_code == 200
    assert analyzed.json()["final_action"] == "APPROVE"

    audit = client.get(f"/api/payment-requests/{first.json()['request_id']}/audit")
    assert audit.status_code == 200
    assert audit.json()["decision_hash"].startswith("0x")


def test_review_payment_can_be_manually_approved_then_fail_closed_on_execute(client: TestClient):
    payload = {
        "vendor_id": "vendor_demo",
        "invoice_id": "inv_demo_002",
        "amount_units": 700_000_000,
        "recipient_address": "0x2222222222222222222222222222222222222222",
    }
    created = client.post("/api/payment-requests", json=payload, headers={"Idempotency-Key": "idem-2"})
    request_id = created.json()["request_id"]

    analyzed = client.post(f"/api/payment-requests/{request_id}/analyze")
    assert analyzed.json()["final_action"] == "REJECT"

    approved = client.post(
        f"/api/payment-requests/{request_id}/approve",
        json={"approver": "finance@example.com", "reason": "manual test approval"},
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "APPROVED"

    executed = client.post(f"/api/payment-requests/{request_id}/execute")
    assert executed.status_code == 503


def test_recoverable_endpoint_returns_confirming_records(client: TestClient):
    payload = {
        "vendor_id": "vendor_demo",
        "invoice_id": "inv_demo_001",
        "amount_units": 420_000_000,
        "recipient_address": "0x1111111111111111111111111111111111111111",
    }
    created = client.post("/api/payment-requests", json=payload, headers={"Idempotency-Key": "idem-3"})
    request_id = created.json()["request_id"]
    client.post(f"/api/payment-requests/{request_id}/analyze")

    repo = routes.get_repository()
    repo.mark_confirming(request_id)

    recoverable = client.get("/api/execution/recoverable")
    assert recoverable.status_code == 200
    assert [item["request_id"] for item in recoverable.json()] == [request_id]
