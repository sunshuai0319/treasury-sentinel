from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_payment_request_is_idempotent_and_analyzable():
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

    analyzed = client.post(f"/api/payment-requests/{first.json()['request_id']}/analyze")
    assert analyzed.status_code == 200
    assert analyzed.json()["final_action"] == "APPROVE"

    audit = client.get(f"/api/payment-requests/{first.json()['request_id']}/audit")
    assert audit.status_code == 200
    assert audit.json()["decision_hash"].startswith("0x")


def test_unapproved_payment_cannot_execute():
    payload = {
        "vendor_id": "vendor_demo",
        "invoice_id": "inv_demo_002",
        "amount_units": 700_000_000,
        "recipient_address": "0x2222222222222222222222222222222222222222",
    }
    created = client.post("/api/payment-requests", json=payload, headers={"Idempotency-Key": "idem-2"})
    request_id = created.json()["request_id"]

    analyzed = client.post(f"/api/payment-requests/{request_id}/analyze")
    assert analyzed.json()["final_action"] == "REVIEW"

    executed = client.post(f"/api/payment-requests/{request_id}/execute")
    assert executed.status_code == 409
