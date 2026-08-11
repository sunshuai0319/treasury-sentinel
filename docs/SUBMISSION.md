# Treasury Sentinel

**Policy-aware autonomous treasury agent** for the KeeperHub Agents Onchain hackathon — an
agentic payment system that can prove *why* an AI is allowed to move money, and where a
smart contract guarantees it cannot exceed its authority even when the AI is wrong.

> Real USDC payments have been executed on **Base Sepolia** through KeeperHub. Every claim
> below is backed by on-chain evidence and a runnable codebase.

---

## Demo video

> 📹 **Watch the demo:** [Treasury Sentinel — Agentic Treasury Demo](https://youtu.be/ngtl2ls2bnE)

---

## Highlights

- **Real on-chain execution, not a mock.** Live USDC transfers were submitted through
  KeeperHub Direct Execution and confirmed on Base Sepolia (see [evidence](#real-on-chain-evidence)).
- **Dual-agent reasoning.** A Primary agent judges payment intent against policy; a Critic
  agent independently challenges the decision and can *escalate* risk but never downgrade it.
- **Deterministic safety on top of the LLM.** A pure-code rule engine and an on-chain
  `TreasuryGuard` contract enforce amount, wallet, invoice-uniqueness, budget and pause
  constraints that no model output can override.
- **Decision proof.** Each payment links request → policy citations → agent steps → rule
  results → decision hash → KeeperHub execution ID → transaction hash → contract events.
- **Five reproducible demo scenarios**, a bilingual onboarding kit, and a full test suite.

---

## Why this is not "just another payment agent"

A common agentic-payment demo stops at "the AI decided to pay." Treasury Sentinel inverts
the problem. The LLM *recommends*; the ground truth comes from:

1. **PostgreSQL** — the business source of truth for vendors, invoices, budgets, approvals,
   and execution records (never from model output).
2. **Milvus + local BGE embeddings** — policy retrieval returns citable policy clauses; low
   scores, version conflicts, or Milvus outages **fail closed to human review**.
3. **Deterministic rule engine** — hard checks (amount limits, wallet match, duplicate
   invoice) with final say.
4. **TreasuryGuard (Solidity, Base Sepolia)** — the un-bypassable last line of defense:
   role-gated, pausable, reentrancy-guarded, with per-payment / per-vendor / daily limits,
   invoice-hash uniqueness, and decision expiry.

The core claim:

> The system can prove why the AI is allowed to pay, and the contract guarantees the AI
> cannot pay beyond its authority even when its judgment is wrong.

---

## Architecture

```
Next.js console ──► FastAPI ──► LangGraph ──► Policy retrieval ──► Milvus (+ BGE embeddings)
                          │            │
                          │            └─► Primary Agent ──► Critic Agent
                          │                        │
                          ▼                        ▼
                     PostgreSQL               Deterministic Rule Engine
                     (source of truth)              │
                                                    ▼
                                          KeeperHub Direct Execution
                                                    │
                                                    ▼
                                            TreasuryGuard (Base Sepolia)
```

**Agent state machine:** `validate → retrieve → primary → critic → rules → human/execute →
confirm`.

**Decision priority (strict order):**
`smart-contract constraints > deterministic rules > human approval > Critic > Primary`.

Any tool timeout, model failure, schema error, policy conflict, or unknown on-chain state
**fails closed** — the request goes to human review, never to automatic payment.

---

## Real on-chain evidence

Chain: **Base Sepolia (`84532`)** · Explorer: [sepolia.basescan.org](https://sepolia.basescan.org)

| Item | Address / value |
| --- | --- |
| TreasuryGuard (current) | [`0xE4F52719FC5696e5d746e25E9224518e13f0CEf9`](https://sepolia.basescan.org/address/0xE4F52719FC5696e5d746e25E9224518e13f0CEf9) |
| MockUSDC | [`0x8eEf98476B371BF01D99CBCEA4D7745B49040c95`](https://sepolia.basescan.org/address/0x8eEf98476B371BF01D99CBCEA4D7745B49040c95) |
| KeeperHub EVM wallet | `0x7836A8deB72B27F94d0dF555E23d684aDC894Fe6` (has `EXECUTOR_ROLE` + `GUARDIAN_ROLE`) |
| Chain ID | `84532` |

**Verified payment** (payment request `pay_9cd3b0932166`, executed via KeeperHub):

| Field | Value |
| --- | --- |
| KeeperHub execution ID | `eaeyxg0igy4f9kovtib51` |
| Status | `CONFIRMED` |
| Transaction | [`0xbcbf32c209b3f149408567720253129445c2c356221a4e412ca39d301531a47a`](https://sepolia.basescan.org/tx/0xbcbf32c209b3f149408567720253129445c2c356221a4e412ca39d301531a47a) |
| Receipt status | `0x1` (success) |
| Block | `0x2b003d2` |

The receipt contains a MockUSDC `Transfer` log and a TreasuryGuard `PaymentExecuted` log.
The broadcast was preceded by a KeeperHub `simulate=true` dry-run (`success=true`,
`wouldRevert=false`) — **never broadcast a transaction that simulation says will revert.**

The current TreasuryGuard was redeployed after a first version capped single payments at
500 USDC (legacy `0xcC615A47...`), which reverted approved 500–2000 USDC payments with
`PaymentTooLarge`. The new Guard raises the single-payment cap to **2000 USDC** and daily
limit to **8000 USDC**, unlocking the finance-approval execution path. Two executions on the
new contract (`ni83o7v0mvu33s81pmapj`, `sdqyd4m3c46luwokcyxhl`) are both `CONFIRMED`.

---

## Five demo scenarios

| # | Scenario | Expected outcome |
| --- | --- | --- |
| 1 | Approved vendor, ≤ 500 USDC | **APPROVE** → auto-execute on chain |
| 2 | Duplicate invoice | **REJECT** (rule + contract double protection) |
| 3 | Recipient ≠ vendor wallet | **REJECT** |
| 4 | 500–2000 USDC | **REVIEW** → finance-manager approval → execute |
| 5 | Repeated address anomalies | **PAUSE** → agent calls contract `pause()` |

---

## Verified results

| Check | Result |
| --- | --- |
| API tests (`pytest`) | `64 passed` (idempotency, duplicate-invoice, tx-hash backfill, no-double-pay) |
| Rule engine + repository | table-driven approve / review / reject matrix |
| Contract tests (`hardhat test`) | `5 passing` — roles, pause, limits, expiry, reentrancy |
| Web (`lint` + `typecheck` + `build` + `test:e2e`) | all green (11 Playwright tests) |
| RAG evaluation | Recall@5, Citation, Version Filter, Fail-closed — all `1.00` |
| `check_environment.py` | validates PG, Milvus, model, RPC, contract roles/balances, KeeperHub |

---

## How to run

Full bilingual quick start is in `starter-kit/QUICKSTART.md` / `QUICKSTART.zh-CN.md` and
`README.md`. Environment preflight without printing secrets:

```bash
cd apps/api
uv run python ../../starter-kit/scripts/check_environment.py
```

---

## Repository map

```
apps/web        Next.js demo console (payments, approvals, audit, SSE timeline)
apps/api        FastAPI + LangGraph, deterministic rules, Milvus/BGE retrieval,
                KeeperHub adapter, execution-recovery worker
contracts       TreasuryGuard (Solidity), tests, deploy scripts, deployments/
knowledge       golden policies, deterministic fixtures, RAG golden set, ingestion
starter-kit     reusable KeeperHub adapter, bilingual quickstart, troubleshooting
docs/           architecture, security model, demo script, RAG evaluation
```

**References:** [KeeperHub Agents](https://keeperhub.com/agents) ·
[KeeperHub Docs](https://docs.keeperhub.com/intro/overview) ·
[Architecture](architecture.md) · [Security model](security-model.md) ·
[Integration evidence](keeperhub-integration.md)
