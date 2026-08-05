from app.agent.graph import TreasuryAgentGraph


def test_langgraph_routes_approved_payment_to_final_approve():
    graph = TreasuryAgentGraph(
        policy_retriever=lambda _: [
            {
                "document_id": "payment-policy",
                "section_id": "2.1",
                "title": "自动付款",
                "content": "approved vendor and <= 500 USDC can auto pay",
            }
        ]
    )

    run = graph.run(
        {
            "request_id": "pay_test",
            "invoice_id": "inv_1",
            "vendor_id": "vendor_1",
            "amount_units": 420_000_000,
            "vendor_status": "APPROVED",
            "vendor_wallet": "0x1111111111111111111111111111111111111111",
            "recipient_address": "0x1111111111111111111111111111111111111111",
        }
    )

    assert run.final_action == "APPROVE"
    assert [item.actor for item in run.timeline] == ["primary", "critic", "final"]
    assert run.timeline[-1].policy_refs


def test_langgraph_fails_closed_when_policy_retrieval_fails():
    def fail(_: str):
        raise RuntimeError("milvus unavailable")

    run = TreasuryAgentGraph(policy_retriever=fail).run(
        {
            "request_id": "pay_test",
            "invoice_id": "inv_1",
            "vendor_id": "vendor_1",
            "amount_units": 420_000_000,
            "vendor_status": "APPROVED",
            "vendor_wallet": "0x1111111111111111111111111111111111111111",
            "recipient_address": "0x1111111111111111111111111111111111111111",
        }
    )

    assert run.final_action == "REVIEW"
    assert "policy retrieval failed" in run.timeline[-1].reasons[0]
