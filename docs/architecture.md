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
