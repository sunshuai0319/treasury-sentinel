import asyncio
import json
import time
from datetime import datetime
from functools import lru_cache

import httpx
from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Query, Response, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.agent.demo import run_demo_scenario
from app.agent.state import PaymentRun
from app.config import Settings, get_settings
from app.db import session_factory
from app.integrations.keeperhub import KeeperHubClient
from app.services.execution_payload import build_treasury_execution_payload
from app.services.llm_decisions import get_live_llm_decision_provider
from app.services.payment_workflow import PaymentRequestRecord, PaymentWorkflowRepository
from app.services.policy_retrieval import get_live_policy_retriever

router = APIRouter()


class HealthCheck(BaseModel):
    status: str
    chain_id: int
    treasury_guard_configured: bool
    demo_usdc_configured: bool
    keeperhub_configured: bool


class CreatePaymentRequest(BaseModel):
    vendor_id: str = Field(min_length=1)
    invoice_id: str = Field(min_length=1)
    amount_units: int = Field(gt=0)
    recipient_address: str = Field(pattern=r"^0x[a-fA-F0-9]{40}$")


class ApprovePaymentRequest(BaseModel):
    approver: str = Field(min_length=1)
    reason: str = ""


class RejectPaymentRequest(BaseModel):
    approver: str = Field(min_length=1)
    reason: str = ""


class PaymentRequestView(BaseModel):
    request_id: str
    vendor_id: str
    invoice_id: str
    amount_units: int
    recipient_address: str
    status: str
    final_action: str | None
    decision_hash: str | None
    keeperhub_execution_id: str | None
    transaction_hash: str | None
    created_at: datetime


def to_view(record: PaymentRequestRecord) -> PaymentRequestView:
    return PaymentRequestView(
        request_id=record.request_id,
        vendor_id=record.vendor_id,
        invoice_id=record.invoice_id,
        amount_units=record.amount_units,
        recipient_address=record.recipient_address,
        status=record.status,
        final_action=record.final_action,
        decision_hash=record.decision_hash,
        keeperhub_execution_id=record.keeperhub_execution_id,
        transaction_hash=record.transaction_hash,
        created_at=record.created_at,
    )


@lru_cache(maxsize=1)
def get_repository() -> PaymentWorkflowRepository:
    return PaymentWorkflowRepository(session_factory(get_settings()))


@lru_cache(maxsize=1)
def get_keeperhub_client() -> KeeperHubClient:
    settings = get_settings()
    return KeeperHubClient(settings.keeperhub_api_key, settings.keeperhub_base_url)


def execution_configured(settings: Settings) -> bool:
    return bool(
        settings.keeperhub_api_key
        and settings.keeperhub_wallet_address
        and settings.treasury_guard_address
        and settings.demo_usdc_address
    )


async def submit_treasury_execution(
    *,
    repo: PaymentWorkflowRepository,
    keeperhub_client: KeeperHubClient,
    settings: Settings,
    request_id: str,
    idempotency_key: str | None,
) -> PaymentRequestRecord | None:
    """将已 APPROVED 的付款请求提交到 KeeperHub 上链执行。

    幂等:已存在 execution_id 的请求直接返回,不重复广播。
    配置缺失时静默返回(保持 APPROVED),等待配置齐全后由手动 execute 端点补执行。
    """
    record = repo.get(request_id)
    if not record:
        return None
    if record.keeperhub_execution_id:
        return record
    if record.final_action != "APPROVE" or not record.decision_hash:
        return record
    wallet = settings.keeperhub_wallet_address
    treasury_guard = settings.treasury_guard_address
    token = settings.demo_usdc_address
    if not (settings.keeperhub_api_key and wallet and treasury_guard and token):
        return record
    payload = build_treasury_execution_payload(
        chain_id=settings.chain_id,
        treasury_guard_address=treasury_guard,
        token_address=token,
        keeperhub_wallet_address=wallet,
        recipient_address=record.recipient_address,
        amount_units=record.amount_units,
        invoice_id=record.invoice_id,
        vendor_id=record.vendor_id,
        decision_hash=record.decision_hash,
    )
    try:
        execution = await keeperhub_client.execute_payment(
            payload.keeperhub_payload(), idempotency_key=idempotency_key
        )
    except httpx.HTTPError as exc:
        repo.mark_execution_blocked(request_id, f"KeeperHub execution failed: {exc}")
        return repo.get(request_id)
    # 初始响应可能不含 tx hash(链上确认异步);主动回查一次补全,
    # 避免执行后 tx 凭证缺失、只能等 worker 轮询
    if not execution.transaction_hash and execution.execution_id:
        try:
            execution = await keeperhub_client.get_status(execution.execution_id)
        except httpx.HTTPError:
            pass
    return repo.update_execution_status(
        request_id=request_id,
        execution_id=execution.execution_id,
        status=execution.status,
        transaction_hash=execution.transaction_hash,
        error_code=execution.error_code,
    )


@router.get("/health")
def health() -> HealthCheck:
    settings = get_settings()
    return HealthCheck(
        status="ok",
        chain_id=settings.chain_id,
        treasury_guard_configured=bool(settings.treasury_guard_address),
        demo_usdc_configured=bool(settings.demo_usdc_address),
        keeperhub_configured=bool(settings.keeperhub_api_key and settings.keeperhub_wallet_address),
    )


@router.get("/demo/scenarios")
def scenarios() -> list[dict[str, str]]:
    return [
        {"id": "normal", "name": "Normal auto payment"},
        {"id": "duplicate", "name": "Duplicate invoice rejected"},
        {"id": "address_mismatch", "name": "Wallet mismatch rejected"},
        {"id": "over_limit", "name": "Finance review required"},
        {"id": "pause", "name": "Emergency pause recommended"},
    ]


@router.post("/demo/run/{scenario}", response_model=PaymentRun)
def run_scenario(scenario: str) -> PaymentRun:
    return run_demo_scenario(scenario)


@router.post(
    "/payment-requests",
    response_model=PaymentRequestView,
    status_code=status.HTTP_201_CREATED,
)
def create_payment_request(
    payload: CreatePaymentRequest,
    response: Response,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
) -> PaymentRequestView:
    record = get_repository().create(
        idempotency_key=idempotency_key,
        vendor_id=payload.vendor_id,
        invoice_id=payload.invoice_id,
        amount_units=payload.amount_units,
        recipient_address=payload.recipient_address,
    )
    if record.idempotency_key == idempotency_key and record.status != "SUBMITTED":
        response.status_code = status.HTTP_200_OK
    return to_view(record)


@router.get("/payment-requests/{request_id}", response_model=PaymentRequestView)
def get_payment_request(request_id: str) -> PaymentRequestView:
    record = get_repository().get(request_id)
    if not record:
        raise HTTPException(status_code=404, detail="payment request not found")
    return to_view(record)


@router.post("/payment-requests/{request_id}/analyze")
async def analyze_payment_request(
    request_id: str,
    background_tasks: BackgroundTasks,
    response: Response,
    sync: bool = Query(False),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
) -> PaymentRun | PaymentRequestView:
    repo = get_repository()
    existing = repo.get(request_id)
    if not existing:
        raise HTTPException(status_code=404, detail="payment request not found")
    # 只允许对 SUBMITTED 请求执行分析;已完成(APPROVED/REVIEW/CONFIRMING/CONFIRMED
    # /FAILED/EXECUTION_BLOCKED)的请求直接返回现有状态,避免状态倒退回 APPROVED。
    if existing.status == "ANALYZING":
        if idempotency_key:
            response.status_code = status.HTTP_202_ACCEPTED
        return to_view(existing)
    if existing.status != "SUBMITTED":
        return to_view(existing)
    if sync:
        run = await asyncio.to_thread(
            repo.analyze,
            request_id,
            policy_retriever=get_live_policy_retriever(),
            llm_decision_provider=get_live_llm_decision_provider(),
            doubao_decision_mode=get_settings().doubao_decision_mode,
        )
        if not run:
            raise HTTPException(status_code=404, detail="payment request not found")
        if run.final_action == "APPROVE":
            await submit_treasury_execution(
                repo=repo,
                keeperhub_client=get_keeperhub_client(),
                settings=get_settings(),
                request_id=request_id,
                idempotency_key=idempotency_key or request_id,
            )
        return run

    record = repo.mark_analyzing(request_id)
    if not record:
        raise HTTPException(status_code=404, detail="payment request not found")
    background_tasks.add_task(_run_analysis_background, request_id)
    response.status_code = status.HTTP_202_ACCEPTED
    return to_view(record)


async def _run_analysis_background(request_id: str) -> None:
    try:
        run = await asyncio.to_thread(
            get_repository().analyze,
            request_id,
            policy_retriever=get_live_policy_retriever(),
            llm_decision_provider=get_live_llm_decision_provider(),
            doubao_decision_mode=get_settings().doubao_decision_mode,
        )
        if run and run.final_action == "APPROVE":
            await submit_treasury_execution(
                repo=get_repository(),
                keeperhub_client=get_keeperhub_client(),
                settings=get_settings(),
                request_id=request_id,
                idempotency_key=request_id,
            )
    except Exception as exc:  # noqa: BLE001 - background task must fail closed and unblock SSE/UI
        get_repository().mark_analysis_failed(request_id, f"analysis failed: {type(exc).__name__}: {exc}")


@router.post("/payment-requests/{request_id}/approve", response_model=PaymentRequestView)
async def approve_payment_request(request_id: str, payload: ApprovePaymentRequest) -> PaymentRequestView:
    repo = get_repository()
    record = repo.approve(request_id, payload.approver, payload.reason)
    if not record:
        raise HTTPException(status_code=404, detail="payment request not found")
    record = await submit_treasury_execution(
        repo=repo,
        keeperhub_client=get_keeperhub_client(),
        settings=get_settings(),
        request_id=request_id,
        idempotency_key=request_id,
    ) or record
    return to_view(record)


@router.post("/payment-requests/{request_id}/reject", response_model=PaymentRequestView)
def reject_payment_request(request_id: str, payload: RejectPaymentRequest) -> PaymentRequestView:
    record = get_repository().reject(request_id, payload.approver, payload.reason)
    if not record:
        raise HTTPException(status_code=404, detail="payment request not found")
    return to_view(record)


@router.get("/payment-requests", response_model=list[PaymentRequestView])
def list_payment_requests(status: str | None = Query(None)) -> list[PaymentRequestView]:
    if status:
        return [to_view(record) for record in get_repository().list_by_status(status)]
    return [to_view(record) for record in get_repository().list_all()]


@router.post("/payment-requests/{request_id}/execute", response_model=PaymentRequestView)
async def execute_payment_request(
    request_id: str,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
) -> PaymentRequestView:
    repo = get_repository()
    record = repo.get(request_id)
    if not record:
        raise HTTPException(status_code=404, detail="payment request not found")
    can_retry_legacy_confirming = record.status == "CONFIRMING" and not record.keeperhub_execution_id
    can_retry_blocked_execution = (
        record.status == "EXECUTION_BLOCKED"
        and record.final_action == "APPROVE"
        and not record.keeperhub_execution_id
    )
    if record.status != "APPROVED" and not can_retry_legacy_confirming and not can_retry_blocked_execution:
        raise HTTPException(status_code=409, detail="payment request is not approved")
    settings = get_settings()
    if not execution_configured(settings):
        repo.mark_execution_blocked(request_id, "KeeperHub execution is not configured")
        raise HTTPException(status_code=503, detail="KeeperHub execution is not configured")
    if not record.decision_hash:
        repo.mark_execution_blocked(request_id, "payment request has no decision hash")
        raise HTTPException(status_code=409, detail="payment request has no decision hash")

    record = await submit_treasury_execution(
        repo=repo,
        keeperhub_client=get_keeperhub_client(),
        settings=settings,
        request_id=request_id,
        idempotency_key=idempotency_key or request_id,
    )
    if not record:
        raise HTTPException(status_code=404, detail="payment request not found")
    return to_view(record)


@router.get("/payment-requests/{request_id}/audit", response_model=PaymentRequestView)
def get_payment_audit(request_id: str) -> PaymentRequestView:
    record = get_repository().get(request_id)
    if not record:
        raise HTTPException(status_code=404, detail="payment request not found")
    return to_view(record)


@router.get("/payment-requests/{request_id}/events")
def stream_payment_events(
    request_id: str,
    last_event_id: str | None = Query(None),
) -> StreamingResponse:
    if not get_repository().get(request_id):
        raise HTTPException(status_code=404, detail="payment request not found")

    def event_stream():
        sent_ids: set[str] = set()
        resume_after_id = last_event_id
        deadline = time.monotonic() + 180
        while time.monotonic() < deadline:
            events = get_repository().timeline_events(request_id)
            for item in events:
                if resume_after_id:
                    if item["id"] == resume_after_id:
                        sent_ids.add(item["id"])
                        resume_after_id = None
                    continue
                if item["id"] in sent_ids:
                    continue
                sent_ids.add(item["id"])
                yield (
                    f"id: {item['id']}\n"
                    f"event: {item['event']}\n"
                    f"data: {json.dumps(item['data'], ensure_ascii=False)}\n\n"
                )
            record = get_repository().get(request_id)
            if record and record.status not in {"SUBMITTED", "ANALYZING"}:
                return
            yield f"event: heartbeat\ndata: {json.dumps({'request_id': request_id})}\n\n"
            time.sleep(1)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/execution/recoverable", response_model=list[PaymentRequestView])
def list_recoverable_executions() -> list[PaymentRequestView]:
    return [to_view(record) for record in get_repository().list_recoverable()]
