from app.agent.graph import TreasuryAgentGraph
from app.integrations.doubao import CriticDecision, PrimaryDecision


class FakeLlmDecisionProvider:
    def primary(self, state, policy_refs):
        return PrimaryDecision(
            action="AUTO_EXECUTE",
            risk_score=18,
            reasons=["doubao primary cites policy and sees low risk"],
            citation_ids=["payment-policy#2.1"],
        )

    def critic(self, state, primary, policy_refs):
        return CriticDecision(
            challenge=False,
            blocking_issues=[],
            recommended_action="AUTO_EXECUTE",
        )


class FailingLlmDecisionProvider:
    def primary(self, state, policy_refs):
        raise RuntimeError("ark timeout")

    def critic(self, state, primary, policy_refs):
        raise AssertionError("critic should not run")


class ReviewingLlmDecisionProvider:
    def primary(self, state, policy_refs):
        return PrimaryDecision(
            action="HUMAN_REVIEW",
            risk_score=55,
            reasons=["doubao primary requires human review"],
            citation_ids=["payment-policy#2.2"],
        )

    def critic(self, state, primary, policy_refs):
        return CriticDecision(
            challenge=True,
            blocking_issues=["doubao critic keeps the request in review"],
            recommended_action="HUMAN_REVIEW",
        )


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


def test_langgraph_uses_llm_primary_and_critic_when_provider_is_injected():
    graph = TreasuryAgentGraph(
        policy_retriever=lambda _: [
            {
                "document_id": "payment-policy",
                "section_id": "2.1",
                "title": "自动付款",
                "content": "approved vendor and <= 500 USDC can auto pay",
            }
        ],
        llm_decision_provider=FakeLlmDecisionProvider(),
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
    assert run.timeline[0].reasons == ["doubao primary cites policy and sees low risk"]
    assert run.timeline[1].reasons == [
        "critic found no blocking issue beyond deterministic rules (批评代理在确定性规则之外未发现阻断问题)"
    ]


def test_langgraph_llm_review_is_not_overridden_by_deterministic_approve():
    run = TreasuryAgentGraph(
        policy_retriever=lambda _: [{"document_id": "payment-policy", "section_id": "2.2"}],
        llm_decision_provider=ReviewingLlmDecisionProvider(),
    ).run(
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
    assert run.timeline[-1].action == "REVIEW"
    assert "doubao primary/critic recommended REVIEW" in run.timeline[-1].reasons[1]
    assert "豆包主/批评代理建议 REVIEW" in run.timeline[-1].reasons[1]


def test_langgraph_fails_closed_when_llm_primary_fails():
    run = TreasuryAgentGraph(
        policy_retriever=lambda _: [{"document_id": "payment-policy", "section_id": "2.1"}],
        llm_decision_provider=FailingLlmDecisionProvider(),
    ).run(
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
    assert "doubao primary failed" in run.timeline[-1].reasons[0]
