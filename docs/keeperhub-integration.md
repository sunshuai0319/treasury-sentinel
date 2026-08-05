# KeeperHub Integration

## Current Base Sepolia configuration

| Item | Value |
| --- | --- |
| Chain | Base Sepolia (`84532`) |
| TreasuryGuard | `0xcC615A47EFC313172376341Edd5DAfD0f79f8EB3` |
| MockUSDC | `0x8eEf98476B371BF01D99CBCEA4D7745B49040c95` |
| KeeperHub EVM wallet | `0x7836A8deB72B27F94d0dF555E23d684aDC894Fe6` |
| Demo recipient | `0x1111111111111111111111111111111111111111` |

The KeeperHub wallet has `EXECUTOR_ROLE` for normal approved payments and `GUARDIAN_ROLE` for emergency pause actions. The Guard is funded with 1000 MockUSDC and the demo recipient is allowlisted.

## API execution path

`POST /api/payment-requests/{request_id}/execute` now performs the live execution handoff:

1. Verifies the payment request is `APPROVED`.
2. Verifies KeeperHub API key, KeeperHub wallet, TreasuryGuard and MockUSDC addresses are configured.
3. Builds ABI calldata for:

   ```text
   executePaymentWithExpiry(address,address,uint256,bytes32,bytes32,bytes32,uint256)
   ```

4. Submits the call through `KeeperHubClient.execute_contract_call()`.
5. Writes KeeperHub `execution_id`, status and transaction hash back to PostgreSQL.
6. The execution monitor can later poll the execution status and update the request to `CONFIRMED` or `FAILED`.

The calldata selector is `0xde62cb4b`.

## Manual smoke test

```bash
curl -sS -X POST http://localhost:8000/api/payment-requests \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: manual-test-keeperhub-001' \
  -d '{
    "vendor_id":"vendor_demo",
    "invoice_id":"inv_demo_001",
    "amount_units":420000000,
    "recipient_address":"0x1111111111111111111111111111111111111111"
  }' | jq

curl -sS -X POST http://localhost:8000/api/payment-requests/{request_id}/analyze | jq
curl -sS -X POST http://localhost:8000/api/payment-requests/{request_id}/execute | jq
```

Expected execution response after KeeperHub accepts the call:

```json
{
  "status": "CONFIRMING",
  "keeperhub_execution_id": "exec_...",
  "transaction_hash": "0x..."
}
```

If KeeperHub rejects or is unreachable, the API returns `502` and marks the payment request as `EXECUTION_BLOCKED` for auditability.
