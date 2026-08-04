# Treasury Sentinel

面向 KeeperHub Agents Onchain 黑客松的策略感知自主财资 Agent。

项目使用 PostgreSQL 作为业务事实源，Milvus 做政策 RAG，本地
`bge-small-zh-v1.5` 做嵌入，Doubao Seed 2.1 Pro 做双 Agent 判断，
KeeperHub 负责真实 Base Sepolia 链上执行。

## 快速开始

```bash
cd apps/api
cp .env.example .env
uv sync
uv run pytest
```

生成确定性演示数据：

```bash
PYTHONPATH=. uv run python ../../knowledge/scripts/generate_synthetic_data.py
PYTHONPATH=. uv run python ../../knowledge/scripts/ingest_policies.py --dry-run
```

如果你的 Milvus 使用用户名密码登录，在 `apps/api/.env` 中填写
`MILVUS_USER` 和 `MILVUS_PASSWORD`，`MILVUS_TOKEN` 留空。

正式导入前可以先验证连接，命令不会打印密码：

```bash
PYTHONPATH=../..:. uv run python ../../scripts/check_milvus_connection.py
```

启动前端控制台：

```bash
cd apps/web
cp .env.example .env.local
npm install
npm run dev
```

合约环境：

```bash
cd contracts
cp .env.example .env
npm install
npm test
```

合约 `.env` 每个字段的说明见 `contracts/.env.example`。

项目方案见 `docs/treasury-sentinel-project-plan.md`，实施计划见
`docs/treasury-sentinel-implementation-plan.md`。
