import argparse
import json
from pathlib import Path

from sqlalchemy import delete, select

from app.config import Settings
from app.db import Base, session_factory
from app.domain.tables import (
    AgentRunTable,
    AuditLogTable,
    InvoiceTable,
    PaymentRequestTable,
    RuleEvaluationTable,
    VendorTable,
)

ROOT = Path(__file__).resolve().parents[1]
DEMO_VENDOR_ID = "vendor_demo"
DEMO_INVOICES = {
    "normal": ("inv_demo_001", 420_000_000, "0x1111111111111111111111111111111111111111"),
    "duplicate": ("inv_demo_duplicate", 420_000_000, "0x1111111111111111111111111111111111111111"),
    "address_mismatch": ("inv_demo_mismatch", 420_000_000, "0x2222222222222222222222222222222222222222"),
    "over_limit": ("inv_demo_over_limit", 700_000_000, "0x1111111111111111111111111111111111111111"),
    "pause": ("inv_demo_pause", 420_000_000, "0x2222222222222222222222222222222222222222"),
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=20260804)
    parser.add_argument("--env-file", type=Path, default=ROOT / "apps/api/.env")
    args = parser.parse_args()

    settings = Settings(_env_file=args.env_file)  # type: ignore[call-arg]
    Session = session_factory(settings)
    engine = Session.kw["bind"]
    Base.metadata.create_all(engine)
    demo_run_id = f"demo-{args.seed}"
    with Session() as session:
        request_ids = session.scalars(
            select(PaymentRequestTable.request_id).where(
                PaymentRequestTable.idempotency_key.like(f"{demo_run_id}:%")
            )
        ).all()
        if request_ids:
            session.execute(delete(AgentRunTable).where(AgentRunTable.request_id.in_(request_ids)))
            session.execute(delete(RuleEvaluationTable).where(RuleEvaluationTable.request_id.in_(request_ids)))
            session.execute(delete(AuditLogTable).where(AuditLogTable.request_id.in_(request_ids)))
            session.execute(delete(PaymentRequestTable).where(PaymentRequestTable.request_id.in_(request_ids)))
        session.merge(
            VendorTable(
                vendor_id=DEMO_VENDOR_ID,
                name="Demo Software Vendor",
                status="APPROVED",
                risk_level="LOW",
                category="software",
                wallet_address="0x1111111111111111111111111111111111111111",
                wallet_changed_recently=False,
                max_single_payment_units=500_000_000,
            )
        )
        for scenario, (invoice_id, amount, recipient) in DEMO_INVOICES.items():
            session.merge(
                InvoiceTable(
                    invoice_id=invoice_id,
                    vendor_id=DEMO_VENDOR_ID,
                    amount_units=amount,
                    currency="USDC",
                    category="software",
                    recipient_address=recipient,
                    content_hash=f"{demo_run_id}:{scenario}",
                    status="SUBMITTED",
                )
            )
        session.commit()
    print(json.dumps({"demo_run_id": demo_run_id, "invoices": len(DEMO_INVOICES), "ok": True}, sort_keys=True))


if __name__ == "__main__":
    main()
