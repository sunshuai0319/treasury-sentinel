from sqlalchemy import BigInteger, Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class VendorTable(Base):
    __tablename__ = "vendors"

    vendor_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32), index=True)
    risk_level: Mapped[str] = mapped_column(String(32))
    category: Mapped[str] = mapped_column(String(32))
    wallet_address: Mapped[str] = mapped_column(String(42))
    wallet_changed_recently: Mapped[bool] = mapped_column(Boolean, default=False)
    max_single_payment_units: Mapped[int] = mapped_column(BigInteger)


class InvoiceTable(Base):
    __tablename__ = "invoices"

    invoice_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    vendor_id: Mapped[str] = mapped_column(String(32), index=True)
    amount_units: Mapped[int] = mapped_column(BigInteger)
    currency: Mapped[str] = mapped_column(String(16))
    category: Mapped[str] = mapped_column(String(32))
    recipient_address: Mapped[str] = mapped_column(String(42))
    content_hash: Mapped[str] = mapped_column(String(128), index=True)
    status: Mapped[str] = mapped_column(String(32), default="SUBMITTED")

