from app.db import Base
from app.domain.tables import InvoiceTable, VendorTable


def test_business_tables_are_registered():
    assert VendorTable.__tablename__ in Base.metadata.tables
    assert InvoiceTable.__tablename__ in Base.metadata.tables

