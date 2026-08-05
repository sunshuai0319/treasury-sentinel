import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.domain.tables import InvoiceTable, PaymentRequestTable, VendorTable
from app.integrations.keeperhub import KeeperHubExecution
from app.services.payment_workflow import PaymentWorkflowRepository
from app.workers.execution_monitor import recover_confirming_executions


@pytest.mark.asyncio
async def test_recovery_updates_status_without_reexecuting_payment():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(engine)
    with SessionLocal() as session:
        seed(session)
    repo = PaymentWorkflowRepository(SessionLocal)

    async def get_status(execution_id: str) -> KeeperHubExecution:
        assert execution_id == "exec_123"
        return KeeperHubExecution(
            execution_id=execution_id,
            status="completed",
            transaction_hash="0xabc",
        )

    recovered = await recover_confirming_executions(repo, get_status)

    assert recovered == ["pay_recover"]
    record = repo.get("pay_recover")
    assert record is not None
    assert record.status == "CONFIRMED"
    assert record.transaction_hash == "0xabc"


def seed(session: Session) -> None:
    session.add(
        VendorTable(
            vendor_id="vendor_demo",
            name="Demo Vendor",
            status="APPROVED",
            risk_level="LOW",
            category="software",
            wallet_address="0x1111111111111111111111111111111111111111",
            wallet_changed_recently=False,
            max_single_payment_units=500_000_000,
        )
    )
    session.add(
        InvoiceTable(
            invoice_id="inv_demo",
            vendor_id="vendor_demo",
            amount_units=100_000_000,
            currency="USDC",
            category="software",
            recipient_address="0x1111111111111111111111111111111111111111",
            content_hash="hash_monitor",
        )
    )
    session.add(
        PaymentRequestTable(
            request_id="pay_recover",
            idempotency_key="recover-key",
            vendor_id="vendor_demo",
            invoice_id="inv_demo",
            amount_units=100_000_000,
            recipient_address="0x1111111111111111111111111111111111111111",
            status="CONFIRMING",
            final_action="APPROVE",
            decision_hash="0x123",
            keeperhub_execution_id="exec_123",
        )
    )
    session.commit()
