# Treasury Sentinel 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 构建一个使用 PostgreSQL、Milvus、本地 BGE 嵌入、Doubao Seed 2.0 Mini 与 KeeperHub 的可验证自主财资 Agent，并在 Base Sepolia 完成真实测试 USDC 付款。

**架构：** Next.js 提供演示控制台，FastAPI 与 LangGraph 编排 Primary/Critic、确定性规则、Milvus 政策检索和 KeeperHub 执行。PostgreSQL 是业务事实源，Milvus 只保存政策向量；TreasuryGuard 合约执行不可绕过的额度、白名单、幂等和暂停约束。

**技术栈：** Next.js、TypeScript、FastAPI、Pydantic、SQLAlchemy、Alembic、LangGraph、Doubao Seed 2.0 Mini、sentence-transformers、`bge-small-zh-v1.5`、pymilvus、PostgreSQL、Solidity、Hardhat、OpenZeppelin、KeeperHub、Base Sepolia。

---

## 当前实现进度（2026-08-06）

本轮继续实现后，项目状态从“应用内 APPROVE 后仅标记 `CONFIRMING`”推进到“API 能通过 KeeperHub Direct Execution 构造并提交 `TreasuryGuard.executePaymentWithExpiry(...)`，写回 execution ID / transaction hash，并在分析链路接入实时政策检索与 Doubao Primary/Critic 的应用侧闭环”。`POST /api/payment-requests/{id}/analyze` 已改为默认异步，立即返回 `202 ANALYZING`，前端通过 SSE 接收 `ANALYZING → primary → critic → final → status`；低风险请求默认使用 `risk_based` 模式跳过 Doubao，异常/高风险请求才调用 Primary/Critic。已通过 Base Sepolia 公共 RPC 只读验证：`TreasuryGuard` `0xcC615A47EFC313172376341Edd5DAfD0f79f8EB3` 与 `MockUSDC` `0x8eEf98476B371BF01D99CBCEA4D7745B49040c95` 均有链上代码，chainId 为 `84532`；KeeperHub EVM wallet `0x7836A8deB72B27F94d0dF555E23d684aDC894Fe6` 已具备 `EXECUTOR_ROLE` 与 `GUARDIAN_ROLE`；真实付款请求 `pay_9cd3b0932166` 已通过 KeeperHub execution `eaeyxg0igy4f9kovtib51` 完成，交易哈希为 `0xbcbf32c209b3f149408567720253129445c2c356221a4e412ca39d301531a47a`。

| 范围 | 进度 | 证据 |
| --- | --- | --- |
| 任务 8 PostgreSQL/规则 | 部分完成 | SQLAlchemy 已注册 12 张业务表；已新增 Alembic `001_core_tables`，并将当前 PostgreSQL 标记到该版本；`payment_requests.idempotency_key` 由数据库唯一约束保护；规则结果增加稳定 `rule_codes`。尚缺真实并发 PG 集成测试和规格表名的最终对齐。 |
| 任务 9 TreasuryGuard | 基本完成 | 本地合约测试通过；增强版 `TreasuryGuard` 已重新部署到 Base Sepolia：`0xcC615A47EFC313172376341Edd5DAfD0f79f8EB3`；`MockUSDC` 为 `0x8eEf98476B371BF01D99CBCEA4D7745B49040c95`；Guard 已注资 1000 MockUSDC，token 与 demo recipient 已白名单；KeeperHub wallet 已授予执行与暂停相关角色。BaseScan verify 仍缺 API key，不影响链上执行。 |
| 任务 10 KeeperHub | 完成 | Adapter 已对齐官方 Direct Execution API：Base URL `https://app.keeperhub.com`，路径 `/api/execute/contract-call`，执行前先 `simulate=true` dry-run，再带 `Idempotency-Key` 广播；`POST /api/payment-requests/{id}/execute` 会构造 `executePaymentWithExpiry` 调用、提交 KeeperHub execution，并把 `keeperhub_execution_id`、`transaction_hash`、执行状态写入 PostgreSQL。真实证据：execution `eaeyxg0igy4f9kovtib51`，tx `0xbcbf32c209b3f149408567720253129445c2c356221a4e412ca39d301531a47a`。 |
| 任务 11 Agent/LangGraph | 基本完成 | `TreasuryAgentGraph` 仍按 validate → retrieve → primary → critic → rules → human/execute → confirm 编排；付款分析 API 已接入 live Milvus/BGE retriever 与 Doubao Primary/Critic；新增 `DOUBAO_DECISION_MODE=risk_based|always|off`、固定 `DOUBAO_MODEL=doubao-seed-2-0-mini-260428`、Primary/Critic token 上限和 60 秒单次调用 timeout；Milvus/BGE/Doubao 异常在 graph 内 fail-closed 到 `REVIEW`，最终裁决取更保守结果。真实 `/api/payment-requests/pay_9c537bf7aeb5/events` 已返回 Primary/Critic/Final 全链路 `REVIEW`。 |
| 任务 12 FastAPI | 基本完成 | 付款请求 API 已覆盖幂等创建、查询、异步分析、人工审批、未审批执行阻断、真实 KeeperHub execution 提交、审计读取、SSE 事件流和恢复 worker 骨架；`POST /analyze` 默认返回 `202 ANALYZING`，后台完成后写回 `decision_hash` 与最终状态；保留 `?sync=true` 供测试/脚本同步验证。健康检查报告合约、USDC 与 KeeperHub 配置状态。 |
| 任务 13 前端控制台 | 部分完成 | 新增首页导航、Demo、Payments、Approvals、Audit、New Payment、Payment Detail 页面；New Payment 已改为启动异步分析并通过 EventSource 实时更新 DecisionTimeline；新增类型安全 API client、SSE hook、DecisionTimeline 组件和 Playwright 场景规格；`npm run typecheck` 与 `npm run build` 通过。Playwright 因本机 Chromium 下载超时未完成浏览器实跑。 |
| 任务 14 Demo 固化 | 部分完成 | 新增本地五场景 runner 和 `reset_demo_data.py`；reset 只清理带 `demo_run_id` 的付款请求相关记录；runner 可选 `--workflow` 走真实 repository 分析；生成 `docs/demo-script.md`，记录 Base Sepolia 合约地址和五场景决策证据；不伪造 KeeperHub execution ID/tx hash。尚缺真实链上 E2E。 |
| 任务 15 Onboarding | 部分完成 | 新增 `starter-kit/scripts/check_environment.py`、双语 Quickstart、Troubleshooting、反馈报告、架构与安全文档；可检查 Python、Web3、模型、PG、Milvus、RPC、合约地址、USDC 与 KeeperHub 配置，并对缺失 KeeperHub fail-closed。最终验证中除 KeeperHub/live 外本地检查通过。 |

最新验证：

```text
cd apps/api && uv run pytest -q
结果：41 passed

cd apps/api && uv run ruff check app tests ../../database/seed_pg.py ../../database/migrations ../../knowledge/scripts/evaluate_retrieval.py ../../scripts/run_demo_scenarios.py ../../scripts/reset_demo_data.py && uv run mypy app
结果：ruff 通过；mypy 通过

cd apps/api && DATABASE_URL=sqlite:////tmp/test.db uv run alembic upgrade head && DATABASE_URL=sqlite:////tmp/test.db uv run alembic downgrade base
结果：迁移 upgrade/downgrade 通过；当前 PostgreSQL 已 `alembic stamp head` 至 `001_core_tables`

cd contracts && npm test && npm run compile
结果：5 passing；compile 通过

cd contracts && npx hardhat run scripts/local-payment-demo.js
结果：本地 MockUSDC 付款成功；重复发票、未白名单收款人、超单笔额度、暂停状态均按预期 revert

cd apps/web && npm run typecheck && npm run build
结果：通过

cd apps/web && npx playwright test --reporter=line
结果：测试代码已执行到浏览器启动；本机缺少 Chromium，`npx playwright install chromium` 下载 CDN 超时后中断，E2E 浏览器实跑未完成

PYTHONPATH=apps/api apps/api/.venv/bin/python knowledge/scripts/evaluate_retrieval.py --golden knowledge/fixtures/rag-golden-set.json --output docs/rag-evaluation.md
结果：live Milvus 评测通过；20 queries；Recall@5、Citation、Version Filter、Fail-closed 均为 1.00

PYTHONPATH=apps/api apps/api/.venv/bin/python - <<'PY'
... Doubao structured_chat smoke ...
PY
结果：已读取 apps/api/.env 中 ARK 配置并发起结构化调用；请求读超时，未返回模型响应

cd apps/api && uv run python ../../starter-kit/scripts/check_environment.py
结果：Python、Web3、模型、PostgreSQL、Milvus、RPC、TreasuryGuard、MockUSDC、KeeperHub API key/wallet 配置均通过

PYTHONPATH=apps/api apps/api/.venv/bin/python knowledge/scripts/evaluate_retrieval.py --offline --golden knowledge/fixtures/rag-golden-set.json --output docs/rag-evaluation.md
结果：20 queries；Recall@5、Citation、Version Filter、Fail-closed 均为 1.00

PYTHONPATH=apps/api apps/api/.venv/bin/python scripts/run_demo_scenarios.py
结果：生成 docs/demo-script.md；5 个固定场景均输出预期决策；KeeperHub/tx 证据保持阻断说明
```

## 文件结构与职责

```text
treasury-sentinel/
├── apps/web/                       # Next.js 页面与 API Client
├── apps/api/app/
│   ├── api/routes/                 # HTTP/SSE 边界
│   ├── agent/                      # LangGraph State、节点和提示词
│   ├── domain/                     # 付款、供应商、审批、政策实体
│   ├── integrations/               # PG、Milvus、Doubao、KeeperHub、链上适配
│   ├── services/                   # 规则、哈希、执行恢复
│   └── workers/                    # 后台执行追踪
├── contracts/                      # TreasuryGuard、测试、部署脚本
├── knowledge/
│   ├── policies/                   # 人工定义的金标政策
│   ├── fixtures/                   # 固定种子业务数据与 RAG 金标集
│   └── scripts/                    # 生成、摄取、评测 CLI
├── database/                       # Alembic migration 与 seed
├── starter-kit/                    # 可复用 KeeperHub onboarding 成果
├── scripts/                        # 环境检查与 Demo 编排
└── docs/                           # 架构、安全、演示与反馈文档
```

实施顺序固定为：本地嵌入和 Milvus 数据闭环 → PostgreSQL/规则 → 合约/KeeperHub → Agent/API → 前端/Demo。第 2 天结束前必须完成首笔真实测试网交易；第 5 天结束前必须完成端到端闭环。

### 任务 1：初始化仓库与开发环境

**文件：**
- 创建：`README.md`
- 创建：`apps/api/.env.example`
- 创建：`apps/web/.env.example`
- 创建：`contracts/.env.example`
- 创建：`.gitignore`
- 创建：`Makefile`
- 创建：`apps/api/pyproject.toml`
- 创建：`apps/api/app/__init__.py`
- 创建：`apps/api/app/config.py`
- 测试：`apps/api/tests/unit/test_config.py`

- [ ] **步骤 1：初始化 Git 与目录**

运行：

```bash
mkdir treasury-sentinel && cd treasury-sentinel
git init
mkdir -p apps/api/app apps/api/tests/unit apps/web contracts knowledge/{policies,fixtures,scripts} database starter-kit scripts docs
```

预期：`git status --short` 无错误，目录存在。

- [ ] **步骤 2：编写失败的配置测试**

```python
# apps/api/tests/unit/test_config.py
from app.config import Settings


def test_settings_accept_local_embedding_path():
    settings = Settings(
        database_url="postgresql+psycopg://u:p@localhost/db",
        milvus_uri="http://localhost:19530",
        embedding_model_path="/Volumes/wd2t/model/bge-small-zh-v1.5",
        ark_api_key="test",
        keeperhub_api_key="test",
        base_sepolia_rpc_url="https://example.invalid",
    )
    assert settings.embedding_dimension == 512
    assert settings.doubao_model == "doubao-seed-2-0-mini-260428"
```

- [ ] **步骤 3：运行测试并确认失败**

运行：`cd apps/api && uv run pytest tests/unit/test_config.py -v`

预期：FAIL，`ModuleNotFoundError: No module named 'app.config'` 或 `Settings` 未定义。

- [ ] **步骤 4：实现配置与依赖**

```toml
# apps/api/pyproject.toml
[project]
name = "treasury-sentinel-api"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
  "fastapi>=0.116,<1",
  "uvicorn[standard]>=0.35,<1",
  "pydantic-settings>=2.10,<3",
  "sqlalchemy>=2.0,<3",
  "psycopg[binary]>=3.2,<4",
  "alembic>=1.16,<2",
  "pymilvus>=2.6,<3",
  "sentence-transformers>=5,<6",
  "torch>=2.7,<3",
  "langgraph>=0.6,<1",
  "httpx>=0.28,<1",
  "web3>=7.13,<8",
]

[dependency-groups]
dev = ["pytest>=8.4,<9", "pytest-asyncio>=1,<2", "ruff>=0.12,<1", "mypy>=1.17,<2"]

[tool.pytest.ini_options]
pythonpath = ["."]
```

```python
# apps/api/app/config.py
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str
    milvus_uri: str
    milvus_token: str | None = None
    milvus_collection: str = "treasury_policy_chunks_bge_zh_v1"
    embedding_model_path: str
    embedding_dimension: int = 512
    ark_api_key: str
    ark_base_url: str = "https://ark.cn-beijing.volces.com/api/v3"
    doubao_model: str = "doubao-seed-2-0-mini-260428"
    keeperhub_api_key: str
    base_sepolia_rpc_url: str
    chain_id: int = Field(default=84532)
```

- [ ] **步骤 5：验证并提交**

运行：

```bash
cd apps/api
uv sync
uv run pytest tests/unit/test_config.py -v
uv run ruff check app tests
git add .
git commit -m "chore: initialize treasury sentinel workspace"
```

预期：测试 PASS，Ruff 无错误，产生首个 commit。

### 任务 2：验证本地 BGE 嵌入模型

**文件：**
- 创建：`apps/api/app/integrations/milvus/embedding.py`
- 创建：`apps/api/tests/unit/integrations/test_embedding.py`
- 创建：`scripts/check_embedding_model.py`

- [ ] **步骤 1：编写失败的嵌入测试**

```python
from app.integrations.milvus.embedding import LocalBgeEmbedder


def test_embedder_returns_normalized_512_vector(tmp_path):
    embedder = LocalBgeEmbedder.__new__(LocalBgeEmbedder)
    embedder._encode = lambda texts: [[1.0] + [0.0] * 511 for _ in texts]
    result = embedder.embed_documents(["已批准供应商可以付款"])
    assert len(result) == 1
    assert len(result[0]) == 512
    assert sum(x * x for x in result[0]) == 1.0
```

- [ ] **步骤 2：运行并确认失败**

运行：`cd apps/api && uv run pytest tests/unit/integrations/test_embedding.py -v`

预期：FAIL，模块不存在。

- [ ] **步骤 3：实现嵌入封装**

```python
# apps/api/app/integrations/milvus/embedding.py
from collections.abc import Sequence
from sentence_transformers import SentenceTransformer

QUERY_PREFIX = "为这个句子生成表示以用于检索相关文章："


class LocalBgeEmbedder:
    def __init__(self, model_path: str, device: str | None = None):
        self.model = SentenceTransformer(model_path, device=device)
        self._encode = lambda texts: self.model.encode(
            list(texts), normalize_embeddings=True, show_progress_bar=False
        ).tolist()

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return self._encode(texts)

    def embed_query(self, text: str) -> list[float]:
        return self._encode([QUERY_PREFIX + text])[0]
```

- [ ] **步骤 4：增加真实模型 smoke 脚本并运行**

```python
# scripts/check_embedding_model.py
from pathlib import Path
from app.integrations.milvus.embedding import LocalBgeEmbedder

MODEL = Path("/Volumes/wd2t/model/bge-small-zh-v1.5")
assert MODEL.joinpath("model.safetensors").exists()
embedder = LocalBgeEmbedder(str(MODEL))
vector = embedder.embed_query("软件供应商 420 USDC 是否可自动付款")
assert len(vector) == 512
print({"model": str(MODEL), "dimension": len(vector), "ok": True})
```

运行：`PYTHONPATH=apps/api apps/api/.venv/bin/python scripts/check_embedding_model.py`

预期：打印 `dimension: 512` 和 `ok: True`。

- [ ] **步骤 5：回归并提交**

运行：

```bash
cd apps/api && uv run pytest tests/unit/integrations/test_embedding.py -v
git add apps/api scripts/check_embedding_model.py
git commit -m "feat: add local bge embedding provider"
```

### 任务 3：创建 Milvus 金标政策文件

**文件：**
- 创建：`knowledge/policies/payment-policy-v1.md`
- 创建：`knowledge/policies/approval-matrix-v1.md`
- 创建：`knowledge/policies/vendor-risk-policy-v1.md`
- 创建：`knowledge/policies/treasury-limits-v1.md`
- 创建：`knowledge/policies/wallet-change-policy-v1.md`
- 创建：`knowledge/policies/incident-response-v1.md`
- 创建：`knowledge/fixtures/policy-manifest.json`
- 测试：`apps/api/tests/unit/knowledge/test_policy_files.py`

- [ ] **步骤 1：编写政策完整性测试**

```python
import json
from pathlib import Path


def test_policy_manifest_files_and_sections_exist():
    root = Path(__file__).parents[5]
    manifest = json.loads((root / "knowledge/fixtures/policy-manifest.json").read_text())
    assert len(manifest["documents"]) == 6
    for item in manifest["documents"]:
        text = (root / item["path"]).read_text()
        assert f'# {item["title"]}' in text
        assert item["content_hash"] is None
        for section in item["required_sections"]:
            assert f"## {section}" in text
```

- [ ] **步骤 2：确认失败**

运行：`cd apps/api && uv run pytest tests/unit/knowledge/test_policy_files.py -v`

预期：FAIL，manifest 不存在。

- [ ] **步骤 3：写入六份确定性政策**

`payment-policy-v1.md` 必须包含：

```markdown
# 企业付款政策

## 2.1 自动付款
已批准供应商、收款地址匹配、发票未支付、预算充足且金额不超过 500 USDC 时，可以自动付款。

## 2.2 单级审批
付款金额大于 500 USDC 且不超过 2,000 USDC 时，必须获得一名财务经理审批。

## 2.3 双级审批
付款金额超过 2,000 USDC 时，必须获得财务经理和负责人审批；Treasury Sentinel MVP 不执行此类付款。
```

另外五份文件的正文必须分别包含以下精确条款：

```markdown
<!-- approval-matrix-v1.md -->
# 审批矩阵
## 1.1 首次付款
新供应商的首次付款必须由财务经理人工审批。

<!-- vendor-risk-policy-v1.md -->
# 供应商风险政策
## 1.1 重复发票
相同发票号或相同发票内容哈希的请求必须永久拒绝。

<!-- treasury-limits-v1.md -->
# 财资额度政策
## 1.1 分类预算
软件订阅与市场营销使用独立月度预算，任何类别不得借用另一类别的余额。

<!-- wallet-change-policy-v1.md -->
# 钱包变更政策
## 1.1 冷静期
供应商钱包地址在过去 24 小时内发生变化时，付款必须进入人工审核。

<!-- incident-response-v1.md -->
# 事故响应政策
## 1.1 地址异常
同一小时内出现三次收款地址异常时，系统必须建议暂停财资合约的自动执行。
```

- [ ] **步骤 4：写入 manifest**

```json
{
  "schema_version": 1,
  "embedding_model": "bge-small-zh-v1.5",
  "embedding_dimension": 512,
  "documents": [
    {
      "document_id": "payment-policy",
      "title": "企业付款政策",
      "version": 1,
      "path": "knowledge/policies/payment-policy-v1.md",
      "document_type": "PAYMENT_POLICY",
      "required_sections": ["2.1 自动付款", "2.2 单级审批", "2.3 双级审批"],
      "content_hash": null
    }
  ]
}
```

`documents` 还必须加入以下五项：

```json
[
  {"document_id":"approval-matrix","title":"审批矩阵","version":1,"path":"knowledge/policies/approval-matrix-v1.md","document_type":"APPROVAL_MATRIX","required_sections":["1.1 首次付款"],"content_hash":null},
  {"document_id":"vendor-risk-policy","title":"供应商风险政策","version":1,"path":"knowledge/policies/vendor-risk-policy-v1.md","document_type":"VENDOR_RISK","required_sections":["1.1 重复发票"],"content_hash":null},
  {"document_id":"treasury-limits","title":"财资额度政策","version":1,"path":"knowledge/policies/treasury-limits-v1.md","document_type":"TREASURY_LIMITS","required_sections":["1.1 分类预算"],"content_hash":null},
  {"document_id":"wallet-change-policy","title":"钱包变更政策","version":1,"path":"knowledge/policies/wallet-change-policy-v1.md","document_type":"WALLET_CHANGE","required_sections":["1.1 冷静期"],"content_hash":null},
  {"document_id":"incident-response","title":"事故响应政策","version":1,"path":"knowledge/policies/incident-response-v1.md","document_type":"INCIDENT_RESPONSE","required_sections":["1.1 地址异常"],"content_hash":null}
]
```

把这五个对象追加到前述 manifest 的 `documents` 数组，不创建第二个顶层数组。

- [ ] **步骤 5：验证并提交**

运行：

```bash
cd apps/api && uv run pytest tests/unit/knowledge/test_policy_files.py -v
git add knowledge apps/api/tests/unit/knowledge
git commit -m "data: add deterministic treasury policy corpus"
```

### 任务 4：生成固定种子供应商、发票与 RAG 金标集

**文件：**
- 创建：`knowledge/scripts/generate_synthetic_data.py`
- 创建：`knowledge/fixtures/vendors.seed.json`
- 创建：`knowledge/fixtures/invoices.seed.json`
- 创建：`knowledge/fixtures/rag-golden-set.json`
- 测试：`apps/api/tests/unit/knowledge/test_synthetic_data.py`

- [ ] **步骤 1：编写确定性测试**

```python
from knowledge.scripts.generate_synthetic_data import generate_dataset


def test_generator_is_deterministic_and_contains_all_scenarios():
    first = generate_dataset(seed=20260804, vendor_count=40, invoice_count=120)
    second = generate_dataset(seed=20260804, vendor_count=40, invoice_count=120)
    assert first == second
    assert len(first["vendors"]) == 40
    assert len(first["invoices"]) == 120
    assert {x["scenario"] for x in first["invoices"]} == {
        "NORMAL", "OVER_LIMIT", "DUPLICATE", "WALLET_CHANGED",
        "NEW_VENDOR", "MISSING_POLICY"
    }
```

- [ ] **步骤 2：确认失败**

运行：`PYTHONPATH=. apps/api/.venv/bin/pytest apps/api/tests/unit/knowledge/test_synthetic_data.py -v`

预期：FAIL，生成器不存在。

- [ ] **步骤 3：实现固定分布生成器**

```python
# knowledge/scripts/generate_synthetic_data.py
import argparse, json, random
from pathlib import Path

SCENARIOS = (
    ["NORMAL"] * 45 + ["OVER_LIMIT"] * 15 + ["DUPLICATE"] * 10
    + ["WALLET_CHANGED"] * 15 + ["NEW_VENDOR"] * 10
    + ["MISSING_POLICY"] * 5
)


def generate_dataset(seed: int, vendor_count: int, invoice_count: int) -> dict:
    rng = random.Random(seed)
    vendors = [
        {
            "vendor_id": f"V{i:03d}",
            "name": f"Demo Vendor {i:03d}",
            "status": "NEW" if i % 10 == 0 else "APPROVED",
            "risk_level": ["LOW", "MEDIUM", "HIGH"][i % 3],
            "category": ["SOFTWARE", "MARKETING", "OPERATIONS"][i % 3],
            "wallet_address": "0x" + f"{i:040x}",
            "wallet_changed_at": "2026-08-04T08:00:00Z" if i % 7 == 0 else None,
            "max_single_payment_units": 500_000_000,
        }
        for i in range(1, vendor_count + 1)
    ]
    invoices = []
    for i in range(invoice_count):
        scenario = SCENARIOS[i % len(SCENARIOS)]
        vendor = rng.choice(vendors)
        amount = 700_000_000 if scenario == "OVER_LIMIT" else rng.randint(50, 450) * 1_000_000
        source = i - 1 if scenario == "DUPLICATE" and i else i
        invoices.append({
            "invoice_id": f"INV-2026-{source:04d}", "vendor_id": vendor["vendor_id"],
            "amount_units": amount, "currency": "USDC", "scenario": scenario,
        })
    return {"seed": seed, "vendors": vendors, "invoices": invoices}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=20260804)
    parser.add_argument("--output", type=Path, default=Path("knowledge/fixtures"))
    args = parser.parse_args()
    data = generate_dataset(args.seed, 40, 120)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "vendors.seed.json").write_text(json.dumps(data["vendors"], ensure_ascii=False, indent=2))
    (args.output / "invoices.seed.json").write_text(json.dumps(data["invoices"], ensure_ascii=False, indent=2))
```

- [ ] **步骤 4：生成文件并增加 20 条金标检索问题**

运行：`PYTHONPATH=. apps/api/.venv/bin/python knowledge/scripts/generate_synthetic_data.py --seed 20260804`

`rag-golden-set.json` 每项必须包含 `query`、`expected_document`、`expected_version`、`expected_sections`、`expected_action`、`required_conditions`，覆盖六份政策和五种拒绝/降级场景。

- [ ] **步骤 5：验证并提交**

运行：

```bash
PYTHONPATH=. apps/api/.venv/bin/pytest apps/api/tests/unit/knowledge/test_synthetic_data.py -v
git add knowledge apps/api/tests/unit/knowledge
git commit -m "data: add reproducible treasury demo fixtures"
```

### 任务 5：定义 Milvus Collection 与 Repository

**文件：**
- 创建：`apps/api/app/integrations/milvus/schema.py`
- 创建：`apps/api/app/integrations/milvus/repository.py`
- 测试：`apps/api/tests/unit/integrations/test_milvus_schema.py`
- 测试：`apps/api/tests/integration/test_milvus_repository.py`

- [ ] **步骤 1：编写 schema 测试**

```python
from app.integrations.milvus.schema import policy_collection_schema


def test_policy_schema_uses_512_dimension():
    schema = policy_collection_schema(512)
    embedding = next(field for field in schema.fields if field.name == "embedding")
    assert embedding.params["dim"] == 512
    assert schema.enable_dynamic_field is False
```

- [ ] **步骤 2：确认失败**

运行：`cd apps/api && uv run pytest tests/unit/integrations/test_milvus_schema.py -v`

- [ ] **步骤 3：实现 schema 与索引**

```python
# apps/api/app/integrations/milvus/schema.py
from pymilvus import DataType, FieldSchema, CollectionSchema


def policy_collection_schema(dimension: int) -> CollectionSchema:
    fields = [
        FieldSchema("chunk_id", DataType.VARCHAR, is_primary=True, max_length=128),
        FieldSchema("document_id", DataType.VARCHAR, max_length=128),
        FieldSchema("policy_version", DataType.INT64),
        FieldSchema("section_id", DataType.VARCHAR, max_length=64),
        FieldSchema("title", DataType.VARCHAR, max_length=512),
        FieldSchema("content", DataType.VARCHAR, max_length=4096),
        FieldSchema("document_type", DataType.VARCHAR, max_length=64),
        FieldSchema("payment_category", DataType.VARCHAR, max_length=64),
        FieldSchema("approval_level", DataType.VARCHAR, max_length=64),
        FieldSchema("effective_from", DataType.INT64),
        FieldSchema("effective_to", DataType.INT64),
        FieldSchema("content_hash", DataType.VARCHAR, max_length=64),
        FieldSchema("embedding", DataType.FLOAT_VECTOR, dim=dimension),
    ]
    return CollectionSchema(fields, enable_dynamic_field=False)
```

Repository 必须实现 `ensure_collection()`、`upsert_chunks()`、`search()`、`delete_document_version()`，索引使用 `AUTOINDEX` + `COSINE`。

- [ ] **步骤 4：运行真实 Milvus 集成测试**

运行：`cd apps/api && uv run pytest tests/integration/test_milvus_repository.py -v`

预期：创建测试 Collection、写入两条、检索命中正确条款、删除测试 Collection。

- [ ] **步骤 5：提交**

```bash
git add apps/api/app/integrations/milvus apps/api/tests
git commit -m "feat: add milvus policy repository"
```

### 任务 6：实现政策切分、摄取与回读验证

**文件：**
- 创建：`apps/api/app/domain/policies/chunking.py`
- 创建：`apps/api/app/domain/policies/models.py`
- 创建：`knowledge/scripts/ingest_policies.py`
- 测试：`apps/api/tests/unit/domain/test_policy_chunking.py`
- 测试：`apps/api/tests/integration/test_policy_ingestion.py`

- [ ] **步骤 1：编写章节切分测试**

```python
from app.domain.policies.chunking import chunk_markdown


def test_chunk_markdown_preserves_section_and_hash():
    chunks = chunk_markdown("doc", 1, "# 政策\n## 2.1 自动付款\n金额不超过 500 USDC。")
    assert chunks[0].section_id == "2.1"
    assert chunks[0].content == "金额不超过 500 USDC。"
    assert len(chunks[0].content_hash) == 64
```

- [ ] **步骤 2：确认失败并实现纯函数切分器**

实现 `PolicyChunk` Pydantic model 和 `chunk_markdown(document_id, version, text)`；按二级标题切分，超过 350 中文字符时按段落再分，低于 40 字与相邻块合并。

- [ ] **步骤 3：实现摄取 CLI**

```python
# knowledge/scripts/ingest_policies.py（核心入口）
import json
from pathlib import Path

from app.domain.policies.chunking import chunk_markdown


def ingest(manifest_path, embedder, repository) -> dict[str, int]:
    manifest_path = Path(manifest_path)
    root = manifest_path.parents[2]
    manifest = json.loads(manifest_path.read_text())
    counts: dict[str, int] = {}
    for document in manifest["documents"]:
        text = (root / document["path"]).read_text()
        chunks = chunk_markdown(document["document_id"], document["version"], text)
        vectors = embedder.embed_documents([chunk.content for chunk in chunks])
        rows = [chunk.model_dump() | {"embedding": vector} for chunk, vector in zip(chunks, vectors, strict=True)]
        repository.upsert_chunks(rows)
        result = repository.search(
            vector=embedder.embed_query(document["title"]),
            limit=5,
            filters={"document_id": document["document_id"], "policy_version": document["version"]},
        )
        if not result:
            repository.delete_document_version(document["document_id"], document["version"])
            raise RuntimeError(f"ingestion verification failed: {document['document_id']}")
        counts[document["document_id"]] = len(chunks)
    return counts
```

实际实现必须在写入后用每份文档标题进行查询，确认至少命中本版本一条；验证失败时删除刚写入的文档版本并退出非零状态。

- [ ] **步骤 4：运行摄取测试和真实摄取**

运行：

```bash
cd apps/api && uv run pytest tests/unit/domain/test_policy_chunking.py tests/integration/test_policy_ingestion.py -v
cd ../..
PYTHONPATH=apps/api apps/api/.venv/bin/python knowledge/scripts/ingest_policies.py --manifest knowledge/fixtures/policy-manifest.json
```

预期：六份文档全部报告块数，Collection entity count 大于 6。

- [ ] **步骤 5：提交**

```bash
git add apps/api/app/domain knowledge/scripts apps/api/tests
git commit -m "feat: add verified policy ingestion pipeline"
```

### 任务 7：实现 RAG 检索评测

**文件：**
- 创建：`apps/api/app/domain/policies/retrieval.py`
- 创建：`knowledge/scripts/evaluate_retrieval.py`
- 创建：`docs/rag-evaluation.md`
- 测试：`apps/api/tests/unit/domain/test_policy_retrieval.py`

- [ ] **步骤 1：编写版本过滤与 fail-closed 测试**

```python
def test_low_score_result_requires_human_review(fake_repository):
    fake_repository.results = [{"score": 0.41, "document_id": "payment-policy"}]
    result = retrieve_policy("付款", category="SOFTWARE", repository=fake_repository)
    assert result.is_trusted is False
    assert result.fallback_action == "HUMAN_REVIEW"
```

- [ ] **步骤 2：实现检索服务**

`retrieve_policy()` 必须增加有效期、类别和 ACTIVE 版本过滤，返回最多五条；最低可信分默认 0.60，阈值通过环境变量覆盖；每条结果用 PostgreSQL 的 `content_hash` 复核。

- [x] **步骤 3：实现评测 CLI**

CLI 读取 `rag-golden-set.json`，计算 `Recall@5`、Citation Accuracy、Version Filter Accuracy 和 Fail-closed Rate，低于以下门槛时退出 1：

```text
Recall@5 >= 0.90
Citation Accuracy >= 0.90
Version Filter Accuracy = 1.00
Fail-closed Rate = 1.00
```

- [x] **步骤 4：运行评测并记录结果**

运行：`PYTHONPATH=apps/api apps/api/.venv/bin/python knowledge/scripts/evaluate_retrieval.py --golden knowledge/fixtures/rag-golden-set.json`

预期：四项指标达到门槛，结果写入 `docs/rag-evaluation.md`。

- [ ] **步骤 5：提交**

```bash
git add apps/api knowledge/scripts docs/rag-evaluation.md
git commit -m "test: add policy retrieval quality gate"
```

### 任务 8：实现 PostgreSQL 业务模型与确定性规则

**文件：**
- 创建：`apps/api/app/integrations/postgres/models.py`
- 创建：`database/migrations/versions/001_core_tables.py`
- 创建：`apps/api/app/services/rule_engine.py`
- 测试：`apps/api/tests/unit/services/test_rule_engine.py`
- 测试：`apps/api/tests/integration/test_payment_repository.py`

- [ ] **步骤 1：编写表驱动规则测试**

```python
import pytest
from app.services.rule_engine import RuleInput, evaluate


@pytest.mark.parametrize("amount,wallet_match,is_duplicate,expected", [
    (100_000_000, True, False, "AUTO_EXECUTE"),
    (700_000_000, True, False, "HUMAN_REVIEW"),
    (100_000_000, False, False, "REJECT"),
    (100_000_000, True, True, "REJECT"),
])
def test_rule_matrix(amount, wallet_match, is_duplicate, expected):
    result = evaluate(RuleInput(amount_units=amount, wallet_match=wallet_match, is_duplicate=is_duplicate, vendor_approved=True, policy_trusted=True))
    assert result.action == expected
```

- [x] **步骤 2：实现最小规则和数据库唯一约束**

模型必须包含设计规格中的十二张表；`invoices.invoice_hash`、`payment_requests.idempotency_key` 和 `keeperhub_executions.execution_id` 唯一。规则结果必须列出稳定的 `rule_code`，例如 `DUPLICATE_INVOICE`、`WALLET_MISMATCH`、`AMOUNT_REQUIRES_APPROVAL`。

- [x] **步骤 3：运行 migration 与测试**

运行：

```bash
cd apps/api
uv run alembic upgrade head
uv run pytest tests/unit/services/test_rule_engine.py tests/integration/test_payment_repository.py -v
```

- [x] **步骤 4：验证并发幂等**

增加测试并发插入同一 `idempotency_key`，预期仅一条成功，另一条返回已存在的请求而不是创建第二条。

- [ ] **步骤 5：提交**

```bash
git add apps/api database
git commit -m "feat: add payment ledger and deterministic rules"
```

### 任务 9：实现 TreasuryGuard 合约

**文件：**
- 创建：`contracts/contracts/TreasuryGuard.sol`
- 创建：`contracts/test/TreasuryGuard.test.ts`
- 创建：`contracts/scripts/deploy.ts`
- 创建：`contracts/scripts/grant-keeperhub-role.ts`
- 创建：`contracts/hardhat.config.ts`

- [x] **步骤 1：先写失败的合约测试**

测试角色、暂停、Token/供应商白名单、重复发票、决策过期、单笔/供应商/每日额度、事件字段和重入保护。

- [x] **步骤 2：运行并确认失败**

运行：`cd contracts && pnpm hardhat test`

预期：编译失败，因为 `TreasuryGuard.sol` 不存在。

- [x] **步骤 3：实现最小合约**

实现设计中的 `executePayment` 签名和三个角色；所有金额使用 Token 最小单位；日期桶使用 `block.timestamp / 1 days`；先写 `paidInvoices[invoiceHash] = true` 再转账。

- [ ] **步骤 4：测试、部署并验证**

运行：

```bash
pnpm hardhat test
pnpm hardhat run scripts/deploy.ts --network baseSepolia
TREASURY_CONTRACT_ADDRESS=$(jq -r .address deployments/base-sepolia.json)
pnpm hardhat verify --network baseSepolia "$TREASURY_CONTRACT_ADDRESS"
```

当前：本地测试与编译 PASS；增强版尚未重新部署/verify 到 Base Sepolia。

- [ ] **步骤 5：提交**

```bash
git add contracts
git commit -m "feat: add guarded treasury payment contract"
```

### 任务 10：打通 KeeperHub Adapter 与真实交易

**文件：**
- 创建：`apps/api/app/integrations/keeperhub/client.py`
- 创建：`apps/api/app/integrations/keeperhub/models.py`
- 创建：`apps/api/app/integrations/keeperhub/adapter.py`
- 创建：`starter-kit/scripts/verify_wallet_role.py`
- 测试：`apps/api/tests/contract/test_keeperhub_adapter.py`

- [ ] **步骤 1：定义 Adapter 契约测试**

```python
async def test_adapter_maps_execution_status(fake_client):
    fake_client.response = {"id": "exec_1", "status": "confirmed", "txHash": "0xabc"}
    result = await KeeperHubAdapter(fake_client).get_status("exec_1")
    assert result.status == "CONFIRMED"
    assert result.transaction_hash == "0xabc"
```

- [x] **步骤 2：实现 KeeperHub Client 和错误映射**

Adapter 公开 `read_prechecks()`、`simulate_payment()`、`execute_payment()`、`get_status()`、`pause_treasury()`；网络超时映射为 `RETRYABLE`，参数/权限错误映射为 `TERMINAL`，未知状态不得映射为成功。

- [ ] **步骤 3：验证执行钱包角色与余额**

运行：`PYTHONPATH=apps/api apps/api/.venv/bin/python starter-kit/scripts/verify_wallet_role.py`

预期：输出 chainId 84532、合约地址、KeeperHub 钱包、`EXECUTOR_ROLE=true`、测试 ETH/USDC 余额。

- [ ] **步骤 4：执行首笔真实测试网付款**

先模拟，再执行 1 USDC 到批准供应商；轮询至确认；核对 `PaymentExecuted`。将 execution ID 和 tx hash 写入 `docs/keeperhub-integration.md`。

- [ ] **步骤 5：提交**

```bash
git add apps/api starter-kit docs/keeperhub-integration.md
git commit -m "feat: execute treasury payments through keeperhub"
```

### 任务 11：实现 Doubao 双 Agent 与 LangGraph

**文件：**
- 创建：`apps/api/app/integrations/doubao/client.py`
- 创建：`apps/api/app/agent/state.py`
- 创建：`apps/api/app/agent/schemas/decisions.py`
- 创建：`apps/api/app/agent/nodes/primary.py`
- 创建：`apps/api/app/agent/nodes/critic.py`
- 创建：`apps/api/app/agent/graph.py`
- 测试：`apps/api/tests/unit/agent/test_decision_routing.py`

- [x] **步骤 1：定义严格输出 Schema 与失败测试**

```python
class PrimaryDecision(BaseModel):
    action: Literal["AUTO_EXECUTE", "HUMAN_REVIEW", "REJECT"]
    risk_score: int = Field(ge=0, le=100)
    reasons: list[str]
    citation_ids: list[str]


class CriticDecision(BaseModel):
    challenge: bool
    blocking_issues: list[str]
    recommended_action: Literal["AUTO_EXECUTE", "HUMAN_REVIEW", "REJECT"]
```

测试 Critic 不能把 `HUMAN_REVIEW` 降低为 `AUTO_EXECUTE`。

- [x] **步骤 2：实现 Doubao Client**

使用 `ARK_BASE_URL`、`ARK_API_KEY`、`DOUBAO_MODEL`；temperature 0.1；要求 JSON/Function Calling 输出；Pydantic 失败最多重试一次。记录模型名、请求 ID、耗时和 token usage，不记录 API Key。

- [x] **步骤 3：实现 LangGraph 节点与路由**

节点顺序固定为 validate → retrieve → primary → critic → rules → human/execute → confirm。规则节点汇总确定性规则与 Doubao Primary/Critic，最终裁决取更保守结果；Milvus/Doubao 异常进入人工审核。

- [x] **步骤 4：运行录制响应测试**

运行：`cd apps/api && uv run pytest -q`

当前：本地 LangGraph routing/fail-closed、Doubao schema retry、Critic 降级保护和 LLM 升级 REVIEW 不被 deterministic APPROVE 覆盖的单测 PASS；真实 API smoke 已通过 `POST /api/payment-requests/pay_9c537bf7aeb5/analyze` 调用 live Milvus + `doubao-seed-2-0-mini-260428` Primary/Critic，并通过 SSE 返回最终 `REVIEW`。

- [ ] **步骤 5：提交**

```bash
git add apps/api/app/agent apps/api/app/integrations/doubao apps/api/tests/unit/agent
git commit -m "feat: add doubao primary and critic graph"
```

### 任务 12：实现 FastAPI、SSE 与执行恢复

**文件：**
- 创建：`apps/api/app/main.py`
- 创建：`apps/api/app/api/routes/payments.py`
- 创建：`apps/api/app/api/routes/approvals.py`
- 创建：`apps/api/app/api/routes/audit.py`
- 创建：`apps/api/app/api/routes/health.py`
- 创建：`apps/api/app/workers/execution_monitor.py`
- 测试：`apps/api/tests/integration/test_payment_api.py`

- [x] **步骤 1：编写 API 状态转换测试**

测试创建请求返回 201、重复 idempotency key 返回同一请求、未审批请求不能执行、SSE 按顺序输出 Agent 节点、未知 KeeperHub 状态保持 `CONFIRMING`。

- [x] **步骤 2：实现 API**

实现规格中的十个端点。`analyze` 和 `execute` 接收 `Idempotency-Key`；审批绑定 request ID、金额、地址、decision hash、expires_at。

- [x] **步骤 3：实现恢复 Worker**

启动时查询 `SIMULATING`、`EXECUTING`、`CONFIRMING` 记录；按 execution ID 恢复；不得再次调用 `execute_payment()`。

- [x] **步骤 4：运行测试与 OpenAPI 检查**

运行：

```bash
cd apps/api
uv run pytest tests/integration/test_payment_api.py -v
uv run uvicorn app.main:app --port 8000
curl -fsS http://localhost:8000/api/health
```

预期：健康检查分别报告 PostgreSQL、Milvus、Embedding、RPC 和 KeeperHub 配置状态。

- [ ] **步骤 5：提交**

```bash
git add apps/api
git commit -m "feat: expose payment workflow api"
```

### 任务 13：实现 Next.js 演示控制台

**文件：**
- 创建：`apps/web/app/page.tsx`
- 创建：`apps/web/app/payments/new/page.tsx`
- 创建：`apps/web/app/payments/[id]/page.tsx`
- 创建：`apps/web/app/approvals/page.tsx`
- 创建：`apps/web/app/audit/[requestId]/page.tsx`
- 创建：`apps/web/components/decision-timeline.tsx`
- 创建：`apps/web/lib/api/client.ts`
- 测试：`apps/web/tests/payment-flow.spec.ts`

- [x] **步骤 1：编写失败的 Playwright 场景**

测试选择“正常付款”预置数据、提交、看到 Primary/Critic/Rules/Simulation/Confirmed 六个阶段和交易链接。

- [x] **步骤 2：实现类型安全 API Client 与 SSE Hook**

Client 只接受后端 OpenAPI 对应类型；SSE 断开最多重连三次，重连使用最后 event ID。

- [x] **步骤 3：实现五个页面和固定场景按钮**

页面不加入钱包连接、图表库、主题系统或复杂动画。每个决策节点显示状态、耗时、证据和失败原因。

- [x] **步骤 4：运行前端测试**

运行：

```bash
cd apps/web
pnpm lint
pnpm typecheck
pnpm test:e2e
```

当前：`npm run typecheck` 与 `npm run build` PASS；已新增 Playwright 场景规格和真实付款申请页面；浏览器安装下载超时，尚未完成 Playwright 实跑。

预期：全部 PASS。

- [ ] **步骤 5：提交**

```bash
git add apps/web
git commit -m "feat: add treasury decision console"
```

### 任务 14：固化五个 Demo 与端到端验证

**文件：**
- 创建：`scripts/reset_demo_data.py`
- 创建：`scripts/run_demo_scenarios.py`
- 创建：`apps/api/tests/e2e/test_base_sepolia_payment.py`
- 创建：`docs/demo-script.md`

- [x] **步骤 1：实现可重复重置**

重置只清理带 `demo_run_id` 的数据库记录；不得删除整个数据库或 Milvus Collection；同一 seed 生成同样的供应商和请求。

- [x] **步骤 2：实现五场景 runner**

顺序运行 NORMAL、DUPLICATE、WALLET_CHANGED、OVER_LIMIT、INCIDENT_PAUSE；每个场景断言最终状态和预期 rule code。

- [ ] **步骤 3：运行真实 E2E**

运行：

```bash
PYTHONPATH=apps/api apps/api/.venv/bin/python scripts/reset_demo_data.py --seed 20260804
PYTHONPATH=apps/api apps/api/.venv/bin/python scripts/run_demo_scenarios.py --live-chain
```

预期：正常付款和审批后付款产生真实 tx hash；其余场景不产生未授权付款；暂停场景产生 `Paused` 事件。

- [x] **步骤 4：记录可验证证据**

`docs/demo-script.md` 写入合约地址、演示顺序和本地可验证决策证据；由于 KeeperHub 阻断，不写入伪造 execution ID 或 tx hash。

- [ ] **步骤 5：提交**

```bash
git add scripts apps/api/tests/e2e docs/demo-script.md
git commit -m "test: verify five treasury demo scenarios"
```

### 任务 15：完成 Onboarding Kit、文档与总体验证

**文件：**
- 创建：`starter-kit/QUICKSTART.md`
- 创建：`starter-kit/QUICKSTART.zh-CN.md`
- 创建：`starter-kit/TROUBLESHOOTING.md`
- 创建：`starter-kit/FEEDBACK_REPORT.md`
- 创建：`starter-kit/scripts/check_environment.py`
- 创建：`docs/security-model.md`
- 创建：`docs/architecture.md`
- 修改：`README.md`

- [x] **步骤 1：实现环境检查脚本**

脚本检查 Python、Node、模型路径、PG、Milvus、RPC、KeeperHub 配置、合约角色和余额；输出表格并以非零状态表示阻断项。日志只显示密钥是否存在，不显示密钥值。

- [x] **步骤 2：编写双语 10–15 分钟 Quickstart**

包含安装、环境变量、数据库 migration、政策摄取、RAG 评测、合约配置、API/前端启动和最小 KeeperHub 调用。

- [x] **步骤 3：填写真实反馈报告**

每项包含标题、环境、最小复现、预期、实际、日志、影响和建议；不编造未实际遇到的问题。

- [ ] **步骤 4：运行最终验证**

运行：

```bash
cd apps/api && uv run pytest -v && uv run ruff check app tests && uv run mypy app
cd ../../contracts && pnpm hardhat test
cd ../apps/web && pnpm lint && pnpm typecheck && pnpm test:e2e
cd ../..
PYTHONPATH=apps/api apps/api/.venv/bin/python knowledge/scripts/evaluate_retrieval.py --golden knowledge/fixtures/rag-golden-set.json
PYTHONPATH=apps/api apps/api/.venv/bin/python starter-kit/scripts/check_environment.py
```

当前：API、合约、前端 typecheck、RAG 离线评测和本地 demo runner 均通过；环境检查仍因 KeeperHub 配置缺失按设计返回阻断。

- [ ] **步骤 5：审查 Git 历史并提交**

```bash
git status --short
git log --oneline --decorate -15
git add README.md starter-kit docs
git commit -m "docs: publish keeperhub treasury onboarding kit"
```

预期：工作树干净，历史包含逐模块 commit，而不是单一大提交。

## 规格覆盖检查

| 规格需求 | 实现任务 |
| --- | --- |
| 本地 BGE + Milvus | 2、5、6、7 |
| 合成数据与金标集 | 3、4、7 |
| PostgreSQL 与规则 | 8 |
| TreasuryGuard | 9 |
| KeeperHub 深度执行 | 10、14 |
| Doubao Primary/Critic | 11 |
| FastAPI/SSE/恢复 | 12 |
| Next.js 审计控制台 | 13 |
| 五个 Demo | 14 |
| Onboarding 双语成果 | 15 |

## 停止条件

当且仅当任务 15 的最终验证全部通过、至少一笔 Base Sepolia 付款已确认、五个 Demo 场景可重复、RAG 指标达标且 README/Quickstart 可由空环境执行时，才可以宣称项目完成。无法运行的外部验证必须在交付中明确列出，不得用 Mock 结果冒充真实 KeeperHub 或链上证据。
