from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.domain.tables import InvoiceTable, VendorTable
from app.services.payment_workflow import PaymentWorkflowRepository


def test_repository_returns_existing_request_for_duplicate_idempotency_key():
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
    first = repo.create(
        idempotency_key="same-key",
        vendor_id="vendor_demo",
        invoice_id="inv_demo",
        amount_units=100_000_000,
        recipient_address="0x1111111111111111111111111111111111111111",
    )
    second = repo.create(
        idempotency_key="same-key",
        vendor_id="vendor_demo",
        invoice_id="inv_demo",
        amount_units=100_000_000,
        recipient_address="0x1111111111111111111111111111111111111111",
    )

    assert second.request_id == first.request_id


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
            content_hash="hash_repo",
        )
    )
    session.commit()
