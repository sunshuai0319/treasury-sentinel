# KeeperHub Integration

## Current Base Sepolia configuration

| Item | Value |
| --- | --- |
| Chain | Base Sepolia (`84532`) |
| TreasuryGuard | `0xE4F52719FC5696e5d746e25E9224518e13f0CEf9` |
| MockUSDC | `0x8eEf98476B371BF01D99CBCEA4D7745B49040c95` |
| KeeperHub EVM wallet | `0x7836A8deB72B27F94d0dF555E23d684aDC894Fe6` |
| Demo recipient | `0x1111111111111111111111111111111111111111` |

The current TreasuryGuard (`maxSinglePaymentUnits=2000 USDC`, `dailyLimit=8000 USDC`) is a redeploy
that supports the 500–2000 USDC finance-approval execution path (the first deployment at
`0xcC615A47EFC313172376341Edd5DAfD0f79f8EB3` capped single payments at 500 USDC, so approved
payments above that reverted with `PaymentTooLarge`). The KeeperHub wallet has `EXECUTOR_ROLE`
and `GUARDIAN_ROLE`; the Guard is funded with 5000 MockUSDC and the demo recipient is allowlisted.

## API execution path

`POST /api/payment-requests/{request_id}/execute` now performs the live execution handoff:

1. Verifies the payment request is `APPROVED`.
2. Verifies KeeperHub API key, KeeperHub wallet, TreasuryGuard and MockUSDC addresses are configured.
3. Builds ABI calldata for:

   ```text
   executePaymentWithExpiry(address,address,uint256,bytes32,bytes32,bytes32,uint256)
   ```

4. Submits the call through KeeperHub Direct Execution `POST /api/execute/contract-call`.
5. Writes KeeperHub `execution_id`, status and transaction hash back to PostgreSQL.
6. The execution monitor can later poll the execution status and update the request to `CONFIRMED` or `FAILED`.

### Automatic execution (方案 A)

Analysis `APPROVE` and manual `approve` now submit to KeeperHub automatically; the separate
`POST /api/payment-requests/{request_id}/execute` endpoint remains as a manual/retry path:

- Low-risk analysis ending in `APPROVE` → auto-executes right after analysis (sync or async).
- `REVIEW` requests approved by an operator → auto-executes right after `approve`.
- If KeeperHub credentials/wallet/guard/USDC are not configured, execution stays `APPROVED`
  (no broadcast) and can be completed later via the manual `execute` endpoint once configured.
- Idempotency: a request that already has a KeeperHub `execution_id` is never broadcast again.
- Broadcast failure marks the request `EXECUTION_BLOCKED` for auditability; retry via `execute`.

### Execution status polling (worker)

On API startup the lifespan launches `execution_recovery_loop`, which polls KeeperHub
`GET /api/execute/{execution_id}/status` for `SIMULATING`/`EXECUTING`/`CONFIRMING` requests
and advances them to `CONFIRMED`/`FAILED`. Interval is `KEEPERHUB_POLL_INTERVAL_SECONDS`
(default 30); disable with `KEEPERHUB_POLL_ENABLED=false`.

### Backfilling pre-existing APPROVED requests

Requests approved before this change (with no `execution_id`) can be broadcast in bulk:

```bash
PYTHONPATH=apps/api apps/api/.venv/bin/python scripts/backfill_approved_payments.py
```

The script scans `status=APPROVED && final_action=APPROVE && execution_id IS NULL`, submits each
through `submit_treasury_execution` (idempotent, no double-broadcast), and skips requests when
KeeperHub credentials are not configured.

The calldata selector is `0xde62cb4b`.

## Verified execution evidence

> 历史记录:以下执行发生在**旧合约** `0xcC615A47EFC313172376341Edd5DAfD0f79f8EB3`(部署于 2026-08-05,单笔上限 500 USDC)。新合约部署后,当前执行使用 `0xE4F52719FC5696e5d746e25E9224518e13f0CEf9`。

| Field | Value |
| --- | --- |
| Payment request | `pay_9cd3b0932166` |
| KeeperHub execution ID | `eaeyxg0igy4f9kovtib51` |
| Status | `CONFIRMED` |
| Transaction hash | `0xbcbf32c209b3f149408567720253129445c2c356221a4e412ca39d301531a47a` |
| Receipt status | `0x1` |
| Block number | `0x2b003d2` |

Before broadcast, KeeperHub dry-run simulation returned `success=true`, `wouldRevert=false`, and gas estimate `148325`. The final receipt contains a MockUSDC `Transfer` log and a TreasuryGuard `PaymentExecuted` log emitted by `0xcC615A47EFC313172376341Edd5DAfD0f79f8EB3`.

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
