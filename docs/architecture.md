# Treasury Sentinel Architecture

Treasury Sentinel has five local/runtime layers:

1. Next.js console for fixed demo scenarios and payment workflow inspection.
2. FastAPI boundary for health, payment requests, approval, audit, and SSE.
3. PostgreSQL as the business source of truth for vendors, invoices, payment
   requests, rule evaluations, approvals, agent runs, KeeperHub executions, and
   audit logs.
4. Milvus plus local BGE embeddings for policy retrieval.
5. TreasuryGuard on Base Sepolia, executed through KeeperHub when credentials
   and wallet permissions are configured.

The current implementation intentionally fails closed when KeeperHub credentials
are absent. Demo and local tests can prove policy/rule/API/contract behavior,
but live transaction evidence requires KeeperHub execution ID and transaction
hash.

## Execution flow

- Analysis ending in `APPROVE` (low-risk auto-payment) and manual `approve`
  after a `REVIEW` both auto-submit the payment through KeeperHub Direct
  Execution, write back execution id / tx hash, and advance to
  `CONFIRMING`/`CONFIRMED`. The separate `execute` endpoint remains a manual
  retry/backfill path.
- A background `execution_recovery_loop` (started by the API lifespan) polls
  `SIMULATING`/`EXECUTING`/`CONFIRMING` requests and advances them to
  `CONFIRMED`/`FAILED` (`KEEPERHUB_POLL_INTERVAL_SECONDS`, default 30).
- `scripts/backfill_approved_payments.py` broadcasts pre-existing `APPROVED`
  requests that predate automatic execution.
- The analyzer rejects duplicate invoices at analysis time by comparing against
  already-`CONFIRMED` requests (rule 1.1), instead of relying on the contract's
  `InvoiceAlreadyPaid` revert.
