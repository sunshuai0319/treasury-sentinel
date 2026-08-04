# Treasury Sentinel

Policy-aware autonomous treasury agent for the KeeperHub Agents Onchain hackathon.

The project uses PostgreSQL as the business source of truth, Milvus for policy RAG,
local `bge-small-zh-v1.5` embeddings, Doubao Seed 2.1 Pro for dual-agent reasoning,
and KeeperHub for real Base Sepolia execution.

## Quick Start

```bash
cd apps/api
cp .env.example .env
uv sync
uv run pytest
```

Generate deterministic demo data:

```bash
PYTHONPATH=. uv run python ../../knowledge/scripts/generate_synthetic_data.py
PYTHONPATH=. uv run python ../../knowledge/scripts/ingest_policies.py --dry-run
```

For your deployed Milvus with username/password auth, fill
`MILVUS_USER` and `MILVUS_PASSWORD` in `apps/api/.env`.

Before the real import, verify auth without printing the password:

```bash
PYTHONPATH=../..:. uv run python ../../scripts/check_milvus_connection.py
```

Start the API:

```bash
cd apps/api
uv run uvicorn app.main:app --reload --port 8000
```

Start the web app:

```bash
cd apps/web
cp .env.example .env.local
npm install
npm run dev
```

See `docs/treasury-sentinel-project-plan.md` and `docs/treasury-sentinel-implementation-plan.md`.
Contract deployment env fields are documented in `contracts/.env.example`.
Local contract logic can be checked with:

```bash
cd contracts
npm run demo:local
```
