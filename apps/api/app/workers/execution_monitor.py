from collections.abc import Awaitable, Callable

from app.integrations.keeperhub import KeeperHubExecution
from app.services.payment_workflow import PaymentWorkflowRepository

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
