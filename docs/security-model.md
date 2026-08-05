# Security Model

Treasury Sentinel uses layered controls:

- Deterministic rules decide whether a payment can auto-execute, requires
  review, must be rejected, or should pause treasury execution.
- PostgreSQL stores request status, rule codes, decision hashes, approvals,
  execution IDs, transaction hashes, and audit logs.
- KeeperHub is the only live execution path once credentials and wallet role are
  configured.
- TreasuryGuard enforces recipient allowlist, single-payment amount limit,
  duplicate invoice hash blocking, executor role, and pause.

Current known gaps:

- TreasuryGuard still needs the full planned `GUARDIAN_ROLE`, token allowlist,
  vendor/daily budgets, decision expiry, and reentrancy hardening.
- KeeperHub execution cannot be claimed complete until real execution ID,
  transaction hash, and `PaymentExecuted` event evidence are recorded.
- LangGraph/Doubao reasoning is still represented by a deterministic local
  timeline rather than live model calls.
