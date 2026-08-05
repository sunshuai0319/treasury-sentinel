from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from eth_abi import encode
from eth_utils import keccak, to_checksum_address

from app.services.decision_hash import stable_decision_hash

EXECUTE_PAYMENT_WITH_EXPIRY_SIGNATURE = (
    "executePaymentWithExpiry(address,address,uint256,bytes32,bytes32,bytes32,uint256)"
)


@dataclass(frozen=True)
class TreasuryExecutionPayload:
    to: str
    value: str
    data: str
    chain_id: int
    from_address: str
    contract_address: str
    token_address: str
    recipient_address: str
    amount_units: int
    invoice_hash: str
    vendor_id_hash: str
    decision_hash: str
    expires_at: int
    function_signature: str = EXECUTE_PAYMENT_WITH_EXPIRY_SIGNATURE

    def keeperhub_payload(self) -> dict[str, Any]:
        return {
            "chainId": self.chain_id,
            "from": self.from_address,
            "to": self.to,
            "value": self.value,
            "data": self.data,
            "contractAddress": self.contract_address,
            "functionSignature": self.function_signature,
            "arguments": {
                "token": self.token_address,
                "recipient": self.recipient_address,
                "amount": str(self.amount_units),
                "invoiceHash": self.invoice_hash,
                "vendorId": self.vendor_id_hash,
                "decisionHash": self.decision_hash,
                "expiresAt": self.expires_at,
            },
            "metadata": {
                "app": "treasury-sentinel",
                "purpose": "policy-approved-usdc-payment",
            },
        }


def bytes32_hex(value: str) -> str:
    if value.startswith("0x") and len(value) == 66:
        int(value, 16)
        return value.lower()
    return stable_decision_hash({"value": value})


def build_treasury_execution_payload(
    *,
    chain_id: int,
    treasury_guard_address: str,
    token_address: str,
    keeperhub_wallet_address: str,
    recipient_address: str,
    amount_units: int,
    invoice_id: str,
    vendor_id: str,
    decision_hash: str,
    ttl_seconds: int = 900,
) -> TreasuryExecutionPayload:
    invoice_hash = bytes32_hex(invoice_id)
    vendor_id_hash = bytes32_hex(vendor_id)
    decision_hash = bytes32_hex(decision_hash)
    expires_at = int((datetime.now(UTC) + timedelta(seconds=ttl_seconds)).timestamp())
    selector = keccak(text=EXECUTE_PAYMENT_WITH_EXPIRY_SIGNATURE)[:4]
    encoded_args = encode(
        ["address", "address", "uint256", "bytes32", "bytes32", "bytes32", "uint256"],
        [
            to_checksum_address(token_address),
            to_checksum_address(recipient_address),
            amount_units,
            bytes.fromhex(invoice_hash[2:]),
            bytes.fromhex(vendor_id_hash[2:]),
            bytes.fromhex(decision_hash[2:]),
            expires_at,
        ],
    )
    data = "0x" + (selector + encoded_args).hex()
    contract_address = to_checksum_address(treasury_guard_address)
    return TreasuryExecutionPayload(
        to=contract_address,
        value="0",
        data=data,
        chain_id=chain_id,
        from_address=to_checksum_address(keeperhub_wallet_address),
        contract_address=contract_address,
        token_address=to_checksum_address(token_address),
        recipient_address=to_checksum_address(recipient_address),
        amount_units=amount_units,
        invoice_hash=invoice_hash,
        vendor_id_hash=vendor_id_hash,
        decision_hash=decision_hash,
        expires_at=expires_at,
    )
