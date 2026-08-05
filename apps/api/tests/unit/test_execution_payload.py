from app.services.execution_payload import build_treasury_execution_payload, bytes32_hex


def test_bytes32_hex_accepts_existing_hash_and_hashes_plain_text():
    existing = "0x" + "ab" * 32

    assert bytes32_hex(existing) == existing
    assert bytes32_hex("inv_demo_001").startswith("0x")
    assert len(bytes32_hex("inv_demo_001")) == 66


def test_build_treasury_execution_payload_encodes_execute_payment_with_expiry():
    payload = build_treasury_execution_payload(
        chain_id=84532,
        treasury_guard_address="0xcC615A47EFC313172376341Edd5DAfD0f79f8EB3",
        token_address="0x8eEf98476B371BF01D99CBCEA4D7745B49040c95",
        keeperhub_wallet_address="0x7836A8deB72B27F94d0dF555E23d684aDC894Fe6",
        recipient_address="0x1111111111111111111111111111111111111111",
        amount_units=420_000_000,
        invoice_id="inv_demo_001",
        vendor_id="vendor_demo",
        decision_hash="0x" + "12" * 32,
        ttl_seconds=60,
    )

    keeperhub_payload = payload.keeperhub_payload()

    assert payload.data.startswith("0xde62cb4b")
    assert payload.chain_id == 84532
    assert keeperhub_payload["to"] == "0xcC615A47EFC313172376341Edd5DAfD0f79f8EB3"
    assert keeperhub_payload["value"] == "0"
    assert keeperhub_payload["arguments"]["amount"] == "420000000"
    assert keeperhub_payload["functionSignature"].startswith("executePaymentWithExpiry")
