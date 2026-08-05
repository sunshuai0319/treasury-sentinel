# Treasury Sentinel Quickstart

This guide gets a local developer to the verifiable MVP path in about 10-15
minutes, excluding live KeeperHub credentials.

## 1. API setup

```bash
cd apps/api
cp .env.example .env
uv sync
uv run pytest -q
uv run alembic upgrade head
cd ../..
PYTHONPATH=apps/api apps/api/.venv/bin/python database/seed_pg.py
```

## 2. Policy data

```bash
PYTHONPATH=apps/api apps/api/.venv/bin/python knowledge/scripts/ingest_policies.py --dry-run
PYTHONPATH=apps/api apps/api/.venv/bin/python knowledge/scripts/evaluate_retrieval.py --offline
```

The offline gate writes `docs/rag-evaluation.md`.

## 3. Contracts

```bash
cd contracts
npm install
npm test
npm run demo:local
```

Base Sepolia deployment evidence is recorded in
`contracts/deployments/base-sepolia.json`.

## 4. Run API and web

```bash
cd apps/api
uv run uvicorn app.main:app --reload --port 8000
```

```bash
cd apps/web
npm install
npm run dev
```

## 5. Environment check

```bash
cd apps/api
uv run python ../../starter-kit/scripts/check_environment.py
```

The check intentionally fails until `KEEPERHUB_API_KEY` and
`KEEPERHUB_WALLET_ADDRESS` are configured. The application must not broadcast
live transactions without them.
