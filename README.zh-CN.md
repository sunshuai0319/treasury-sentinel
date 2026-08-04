# Treasury Sentinel

面向 KeeperHub Agents Onchain 黑客松的策略感知自主财资 Agent。

项目使用 PostgreSQL 作为业务事实源，Milvus 做政策 RAG，本地
`bge-small-zh-v1.5` 做嵌入，Doubao Seed 2.1 Pro 做双 Agent 判断，
KeeperHub 负责真实 Base Sepolia 链上执行。

## 快速开始

```bash
cp .env.example apps/api/.env
cd apps/api
uv sync
uv run pytest
```

生成确定性演示数据：

```bash
PYTHONPATH=. uv run python ../../knowledge/scripts/generate_synthetic_data.py
PYTHONPATH=. uv run python ../../knowledge/scripts/ingest_policies.py --dry-run
```

项目方案见 `docs/treasury-sentinel-project-plan.md`，实施计划见
`docs/treasury-sentinel-implementation-plan.md`。

