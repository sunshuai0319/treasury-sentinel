"""为存量已 APPROVED 但尚未上链的付款请求补执行 KeeperHub 广播。

适用于方案 A 自动执行上线前已 APPROVED、无 execution_id 的请求(如历史批次)。
幂等:已有 execution_id 的请求不会被重复广播;配置缺失时保持 APPROVED 并跳过。

用法:
    PYTHONPATH=apps/api apps/api/.venv/bin/python scripts/backfill_approved_payments.py
"""

import asyncio

from app.api.routes import submit_treasury_execution
from app.config import Settings
from app.db import session_factory
from app.integrations.keeperhub import KeeperHubClient
from app.services.payment_workflow import PaymentWorkflowRepository


async def main() -> None:
    settings = Settings()
    repo = PaymentWorkflowRepository(session_factory(settings))
    client = KeeperHubClient(settings.keeperhub_api_key, settings.keeperhub_base_url)
    pending = repo.list_pending_auto_execution()
    if not pending:
        print("No pending APPROVED requests to execute.")
        return
    for record in pending:
        updated = await submit_treasury_execution(
            repo=repo,
            keeperhub_client=client,
            settings=settings,
            request_id=record.request_id,
            idempotency_key=record.request_id,
        )
        status = updated.status if updated else "missing"
        print(f"{record.request_id}: {status}")
    print(f"Processed {len(pending)} pending request(s).")


if __name__ == "__main__":
    asyncio.run(main())
