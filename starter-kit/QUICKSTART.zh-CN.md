# Treasury Sentinel 快速开始

本指南用于在 10-15 分钟内跑通本地可验证 MVP 链路；真实 KeeperHub 执行需要额外配置凭证。

## 1. API 初始化

```bash
cd apps/api
cp .env.example .env
uv sync
uv run pytest -q
uv run alembic upgrade head
cd ../..
PYTHONPATH=apps/api apps/api/.venv/bin/python database/seed_pg.py
```

## 2. 政策数据

```bash
PYTHONPATH=apps/api apps/api/.venv/bin/python knowledge/scripts/ingest_policies.py --dry-run
PYTHONPATH=apps/api apps/api/.venv/bin/python knowledge/scripts/evaluate_retrieval.py --offline
```

离线评测会写入 `docs/rag-evaluation.md`。

## 3. 合约

```bash
cd contracts
npm install
npm test
npm run demo:local
```

Base Sepolia 部署证据记录在 `contracts/deployments/base-sepolia.json`。

## 4. 启动 API 和前端

```bash
cd apps/api
uv run uvicorn app.main:app --reload --port 8000
```

```bash
cd apps/web
npm install
npm run dev
```

## 5. 环境检查

```bash
cd apps/api
uv run python ../../starter-kit/scripts/check_environment.py
```

在 `KEEPERHUB_API_KEY` 和 `KEEPERHUB_WALLET_ADDRESS` 未配置前，检查会故意失败；应用也必须保持 fail-closed，不能广播真实交易。
