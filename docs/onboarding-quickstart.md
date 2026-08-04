# Onboarding Quickstart

This guide is for a local hackathon demo. PostgreSQL and Milvus are expected to be
already running.

## 1. API

```bash
cp .env.example apps/api/.env
cd apps/api
uv sync
uv run pytest
PYTHONPATH=../..:. uv run python ../../knowledge/scripts/generate_synthetic_data.py
PYTHONPATH=../..:. uv run python ../../knowledge/scripts/ingest_policies.py --dry-run
uv run uvicorn app.main:app --reload --port 8000
```

For real Milvus ingestion, remove `--dry-run` after setting `MILVUS_URI` and
`EMBEDDING_MODEL_PATH`.

## 2. Contracts

```bash
cd contracts
npm install
npm test
npx hardhat run scripts/deploy.js --network baseSepolia
```

Before live KeeperHub execution, grant the KeeperHub wallet `EXECUTOR_ROLE` or
deploy the demo contract with the KeeperHub wallet as executor.

## 3. Web Console

```bash
cd apps/web
npm install
npm run build
npm run dev
```

Open `http://localhost:3000`. The default API base is
`http://localhost:8000/api`.

## 4. Demo Evidence Checklist

- Policy corpus: `knowledge/policies/*.md`
- Milvus chunks: `knowledge/scripts/ingest_policies.py`
- Business facts: `knowledge/fixtures/vendors.seed.json` and `invoices.seed.json`
- Contract tests: `contracts/test/TreasuryGuard.js`
- Demo scenarios: normal, duplicate, address mismatch, over limit, emergency pause
- Live evidence: KeeperHub execution id, Base Sepolia transaction hash, contract event

