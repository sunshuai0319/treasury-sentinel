import asyncio
import logging
from collections.abc import Awaitable, Callable

from app.integrations.keeperhub import KeeperHubExecution
from app.services.payment_workflow import PaymentWorkflowRepository

logger = logging.getLogger(__name__)

StatusGetter = Callable[[str], Awaitable[KeeperHubExecution]]


async def recover_confirming_executions(
    repository: PaymentWorkflowRepository,
    get_status: StatusGetter,
) -> list[str]:
    recovered: list[str] = []
    for record in repository.list_recoverable():
        if not record.keeperhub_execution_id:
            continue
        execution = await get_status(record.keeperhub_execution_id)
        repository.update_execution_status(
            request_id=record.request_id,
            execution_id=execution.execution_id,
            status=execution.status,
            transaction_hash=execution.transaction_hash,
            error_code=execution.error_code,
        )
        recovered.append(record.request_id)
    return recovered


async def execution_recovery_loop(
    repository: PaymentWorkflowRepository,
    get_status: StatusGetter,
    interval_seconds: float,
    stop_event: asyncio.Event,
) -> None:
    """定期轮询 SIMULATING/EXECUTING/CONFIRMING 请求,推进到 CONFIRMED/FAILED。

    单轮失败不影响后续轮询(worker 必须存活);stop_event 触发后退出。
    """
    while not stop_event.is_set():
        try:
            await recover_confirming_executions(repository, get_status)
        except Exception:
            logger.exception("execution recovery pass failed")
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval_seconds)
        except TimeoutError:
            continue
