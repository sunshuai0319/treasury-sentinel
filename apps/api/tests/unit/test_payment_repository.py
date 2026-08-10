from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.domain.tables import InvoiceTable, PaymentRequestTable, VendorTable
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


def test_list_orders_by_created_at_newest_first():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(engine)
    with SessionLocal() as session:
        seed(session)
        session.add_all(
            [
                PaymentRequestTable(
                    request_id="pay_old",
                    idempotency_key="key-old",
                    vendor_id="vendor_demo",
                    invoice_id="inv_demo",
                    amount_units=100_000_000,
                    recipient_address="0x1111111111111111111111111111111111111111",
                    status="APPROVED",
                    created_at=datetime(2026, 1, 1),
                ),
                PaymentRequestTable(
                    request_id="pay_new",
                    idempotency_key="key-new",
                    vendor_id="vendor_demo",
                    invoice_id="inv_demo",
                    amount_units=100_000_000,
                    recipient_address="0x1111111111111111111111111111111111111111",
                    status="REVIEW",
                    created_at=datetime(2026, 6, 1),
                ),
            ]
        )
        session.commit()

    repo = PaymentWorkflowRepository(SessionLocal)
    assert [r.request_id for r in repo.list_all()] == ["pay_new", "pay_old"]
    assert [r.request_id for r in repo.list_by_status("REVIEW")] == ["pay_new"]
    assert [r.request_id for r in repo.list_by_status("APPROVED")] == ["pay_old"]
