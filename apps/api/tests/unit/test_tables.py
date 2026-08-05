from app.db import Base
from app.domain.tables import (
    AgentRunTable,
    ApprovalTable,
    AuditLogTable,
    BudgetTable,
    ContractEventTable,
    InvoiceTable,
    KeeperHubExecutionTable,
    PaymentRequestTable,
    PolicyVersionTable,
    RuleEvaluationTable,
    VendorTable,
    VendorWalletHistoryTable,
)


def test_business_tables_are_registered():
    expected = {
        VendorTable.__tablename__,
        InvoiceTable.__tablename__,
        VendorWalletHistoryTable.__tablename__,
        PaymentRequestTable.__tablename__,
        ApprovalTable.__tablename__,
        BudgetTable.__tablename__,
        PolicyVersionTable.__tablename__,
        AgentRunTable.__tablename__,
        RuleEvaluationTable.__tablename__,
        KeeperHubExecutionTable.__tablename__,
        ContractEventTable.__tablename__,
        AuditLogTable.__tablename__,
    }
    assert expected.issubset(Base.metadata.tables)
