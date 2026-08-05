import json
from pathlib import Path

from app.config import Settings
from app.db import Base, session_factory
from app.domain.tables import InvoiceTable, VendorTable


def main() -> None:
    root = Path(__file__).parents[1]
    settings = Settings(_env_file=root / "apps/api/.env")  # type: ignore[call-arg]
    Session = session_factory(settings)
    engine = Session.kw["bind"]
    Base.metadata.create_all(engine)
    vendors = json.loads((root / "knowledge/fixtures/vendors.seed.json").read_text())
    invoices = json.loads((root / "knowledge/fixtures/invoices.seed.json").read_text())
    with Session() as session:
        for item in vendors:
            session.merge(
                VendorTable(
                    vendor_id=item["vendor_id"],
                    name=item["name"],
                    status=item["status"],
                    risk_level=item["risk_level"],
                    category=item["category"],
                    wallet_address=item["wallet_address"],
                    wallet_changed_recently=bool(item["wallet_changed_at"]),
                    max_single_payment_units=item["max_single_payment_units"],
                )
            )
        for item in invoices:
            session.merge(
                InvoiceTable(
                    invoice_id=item["invoice_id"],
                    vendor_id=item["vendor_id"],
                    amount_units=item["amount_units"],
                    currency=item["currency"],
                    category=item["category"],
                    recipient_address=item["recipient_address"],
                    content_hash=item["content_hash"],
                )
            )
        session.commit()
    print({"vendors": len(vendors), "invoices": len(invoices)})


if __name__ == "__main__":
    main()
