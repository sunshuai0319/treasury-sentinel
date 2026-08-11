# Treasury Sentinel

面向 KeeperHub Agents Onchain 黑客松的策略感知自主财资 Agent。

项目使用 PostgreSQL 作为业务事实源，Milvus 做政策 RAG，本地
`bge-small-zh-v1.5` 做嵌入，Doubao Seed 2.0 Mini（`doubao-seed-2-0-mini-260428`）
做双 Agent 判断，KeeperHub 负责真实 Base Sepolia 链上执行。

📹 **演示视频：** [Treasury Sentinel — Agentic Treasury Demo](https://youtu.be/ngtl2ls2bnE)

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

启动 API：

```bash
cd apps/api
uv run uvicorn app.main:app --reload --port 8000
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

本地合约业务逻辑可以直接跑：

```bash
cd contracts
npm run demo:local
```

当前 Base Sepolia 部署证据记录在 `contracts/deployments/base-sepolia.json`。
检查本地环境且不打印密钥：

```bash
cd apps/api
uv run python ../../starter-kit/scripts/check_environment.py
```

在 KeeperHub key 和执行钱包地址未配置前，脚本会以非零状态退出，应用侧真实执行也会 fail-closed。

全新数据库先用 Alembic 建表，再 seed 固定数据：

```bash
cd apps/api
uv run alembic upgrade head
cd ../..
PYTHONPATH=apps/api apps/api/.venv/bin/python database/seed_pg.py
```

如果之前已经用旧版 seed 脚本创建过表，确认表存在后只需补一次版本标记：

```bash
cd apps/api
uv run alembic stamp head
```

项目方案见 `docs/treasury-sentinel-project-plan.md`，实施计划见
`docs/treasury-sentinel-implementation-plan.md`。
