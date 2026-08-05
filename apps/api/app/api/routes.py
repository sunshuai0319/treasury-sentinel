from functools import lru_cache

from fastapi import APIRouter, Header, HTTPException, Response, status
from pydantic import BaseModel, Field

from app.agent.demo import run_demo_scenario
from app.agent.state import PaymentRun
from app.config import get_settings
from app.db import session_factory
from app.services.payment_workflow import PaymentRequestRecord, PaymentWorkflowRepository

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
    )


@lru_cache(maxsize=1)
def get_repository() -> PaymentWorkflowRepository:
    return PaymentWorkflowRepository(session_factory(get_settings()))


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


@router.post("/payment-requests/{request_id}/analyze", response_model=PaymentRun)
def analyze_payment_request(request_id: str) -> PaymentRun:
    run = get_repository().analyze(request_id)
    if not run:
        raise HTTPException(status_code=404, detail="payment request not found")
    return run


@router.post("/payment-requests/{request_id}/approve", response_model=PaymentRequestView)
def approve_payment_request(request_id: str, payload: ApprovePaymentRequest) -> PaymentRequestView:
    record = get_repository().approve(request_id, payload.approver, payload.reason)
    if not record:
        raise HTTPException(status_code=404, detail="payment request not found")
    return to_view(record)


@router.post("/payment-requests/{request_id}/execute", response_model=PaymentRequestView)
def execute_payment_request(request_id: str) -> PaymentRequestView:
    repo = get_repository()
    record = repo.get(request_id)
    if not record:
        raise HTTPException(status_code=404, detail="payment request not found")
    if record.status != "APPROVED":
        raise HTTPException(status_code=409, detail="payment request is not approved")
    settings = get_settings()
    if not settings.keeperhub_api_key or not settings.keeperhub_wallet_address:
        repo.mark_execution_blocked(request_id, "KeeperHub execution is not configured")
        raise HTTPException(status_code=503, detail="KeeperHub execution is not configured")
    record = repo.mark_confirming(request_id)
    if not record:
        raise HTTPException(status_code=404, detail="payment request not found")
    return to_view(record)


@router.get("/payment-requests/{request_id}/audit", response_model=PaymentRequestView)
def get_payment_audit(request_id: str) -> PaymentRequestView:
    record = get_repository().get(request_id)
    if not record:
        raise HTTPException(status_code=404, detail="payment request not found")
    return to_view(record)


@router.get("/execution/recoverable", response_model=list[PaymentRequestView])
def list_recoverable_executions() -> list[PaymentRequestView]:
    return [to_view(record) for record in get_repository().list_recoverable()]
