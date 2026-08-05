# Feedback Report

## 1. KeeperHub credentials are a hard demo dependency

Environment: local FastAPI, Base Sepolia, deployed TreasuryGuard and MockUSDC.

Minimum reproduction:

```bash
cd apps/api
uv run python ../../starter-kit/scripts/check_environment.py
```

Expected: clear pass/fail for live execution readiness.

Actual: the project correctly blocks execution when KeeperHub key or wallet is
missing.

Impact: local development can continue, but live execution evidence cannot be
claimed.

Suggestion: keep the fail-closed check and add a credential validation endpoint
once the exact KeeperHub API contract is finalized.

## 2. Existing databases need Alembic stamping

Environment: PostgreSQL database previously initialized with `create_all`.

Minimum reproduction:

```bash
cd apps/api
uv run alembic upgrade head
```

Expected: migration state is tracked.

Actual: already-created tables require `uv run alembic stamp head`.

Impact: developers who used early seed scripts need one extra migration-state
step.

Suggestion: document the stamp path and use Alembic first for new databases.
