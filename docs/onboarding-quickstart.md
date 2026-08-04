# Onboarding Quickstart

This guide is for a local hackathon demo. PostgreSQL and Milvus are expected to be
already running.

## 1. API

```bash
cd apps/api
cp .env.example .env
uv sync
uv run pytest
PYTHONPATH=../..:. uv run python ../../knowledge/scripts/generate_synthetic_data.py
PYTHONPATH=../..:. uv run python ../../knowledge/scripts/ingest_policies.py --dry-run
uv run uvicorn app.main:app --reload --port 8000
```

For real Milvus ingestion, remove `--dry-run` after setting `MILVUS_URI` and
`EMBEDDING_MODEL_PATH`. If Milvus uses username/password auth, set
`MILVUS_USER` and `MILVUS_PASSWORD` in `apps/api/.env`. Leave `MILVUS_TOKEN`
empty in that case.

Check Milvus authentication before importing vectors:

```bash
cd apps/api
PYTHONPATH=../..:. uv run python ../../scripts/check_milvus_connection.py
```

The command masks the password and prints whether a connection was established.
If it returns `UNAUTHENTICATED` or `illegal connection params`, check:

- `MILVUS_USER` and `MILVUS_PASSWORD` are exactly correct; Milvus passwords are
  case-sensitive.
- The common default is often `root` / `Milvus`, not lowercase `milvus`.
- `MILVUS_DB_NAME` is set only when your deployment uses a non-default database.
- `MILVUS_TOKEN` is empty when using username/password.

## 2. Contracts

```bash
cd contracts
cp .env.example .env
npm install
npm test
npm run demo:local
npx hardhat run scripts/deploy.js --network baseSepolia
```

For a persistent local node flow:

```bash
cd contracts
npx hardhat node
```

In another terminal:

```bash
cd contracts
npm run demo:localhost
```

Recommended order before touching Base Sepolia:

1. `npm test` proves the contract invariants.
2. `npm run demo:local` proves the full local payment flow on an in-memory
   Hardhat chain.
3. `npm run demo:localhost` proves the same flow against a persistent local
   Hardhat node.
4. Deploy to Base Sepolia only after the three local checks pass.

Before live KeeperHub execution, grant the KeeperHub wallet `EXECUTOR_ROLE` or
deploy the demo contract with the KeeperHub wallet as executor.

`contracts/.env` fields:

- `BASE_SEPOLIA_RPC_URL`: Base Sepolia RPC endpoint from your RPC provider.
- `DEPLOYER_PRIVATE_KEY`: testnet-only deployer wallet private key. It needs
  Base Sepolia ETH for gas and must not hold mainnet funds.
- `ETHERSCAN_API_KEY`: optional, only needed for later contract verification.

After deployment, copy the deployed `TreasuryGuard` address into
`apps/api/.env` as `TREASURY_GUARD_ADDRESS`. Put the demo USDC address in
`DEMO_USDC_ADDRESS`. The KeeperHub wallet address belongs in
`KEEPERHUB_WALLET_ADDRESS`.

## 3. Web Console

```bash
cd apps/web
cp .env.example .env.local
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
