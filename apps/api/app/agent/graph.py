from collections.abc import Callable
from typing import Any, cast

from langgraph.graph import END, StateGraph

from app.agent.state import AgentDecision, AgentGraphState, PaymentRun
from app.domain.models import Invoice, Vendor
from app.services.rules import evaluate_payment

PolicyRetriever = Callable[[str], list[dict[str, Any]]]


def default_policy_retriever(_: str) -> list[dict[str, Any]]:
    return []


class TreasuryAgentGraph:
    """Deterministic LangGraph shell around retrieval, primary, critic and rules.

    The LLM and Milvus integrations are intentionally injectable. In local CI the
    graph proves routing, validation and fail-closed behavior without requiring
    live external services.
    """

    def __init__(self, policy_retriever: PolicyRetriever | None = None):
        self.policy_retriever = policy_retriever or default_policy_retriever
        builder = StateGraph(AgentGraphState)
        builder.add_node("validate", self._validate)
        builder.add_node("retrieve", self._retrieve)
        builder.add_node("primary", self._primary)
        builder.add_node("critic", self._critic)
        builder.add_node("rules", self._rules)
        builder.add_node("human", self._human)
        builder.add_node("execute", self._execute)
        builder.add_node("confirm", self._confirm)

        builder.set_entry_point("validate")
        builder.add_edge("validate", "retrieve")
        builder.add_edge("retrieve", "primary")
        builder.add_edge("primary", "critic")
        builder.add_edge("critic", "rules")
        builder.add_conditional_edges(
            "rules",
            self._route_after_rules,
            {"human": "human", "execute": "execute"},
        )
        builder.add_edge("human", "confirm")
        builder.add_edge("execute", "confirm")
        builder.add_edge("confirm", END)
        self._graph = builder.compile()

    def run(self, initial: AgentGraphState) -> PaymentRun:
        state = cast(AgentGraphState, self._graph.invoke(initial))
        timeline = [
            AgentDecision.model_validate(item)
            for item in state.get("timeline", [])
            if item.get("actor") in {"primary", "critic", "final"}
        ]
        final_action = state.get("final_action", "REVIEW")
        return PaymentRun(
            request_id=state["request_id"],
            scenario=state.get("scenario", "workflow"),
            invoice_id=state["invoice_id"],
            vendor_id=state["vendor_id"],
            final_action=final_action,
            timeline=timeline,
        )

    def _validate(self, state: AgentGraphState) -> AgentGraphState:
        required = ["request_id", "invoice_id", "vendor_id", "amount_units", "vendor_wallet", "recipient_address"]
        missing = [name for name in required if not state.get(name)]
        if missing:
            return {**state, "error": f"missing required fields: {', '.join(missing)}", "final_action": "REVIEW"}
        return {**state, "error": None}

    def _retrieve(self, state: AgentGraphState) -> AgentGraphState:
        if state.get("error"):
            return state
        query = (
            f"vendor={state['vendor_id']} invoice={state['invoice_id']} "
            f"amount={state['amount_units']} recipient={state['recipient_address']}"
        )
        try:
            evidence = self.policy_retriever(query)
        except (ConnectionError, RuntimeError, ValueError) as exc:
            return {**state, "error": f"policy retrieval failed: {exc}", "policy_evidence": []}
        return {**state, "policy_evidence": evidence}

    def _primary(self, state: AgentGraphState) -> AgentGraphState:
        if state.get("error"):
            return state
        refs = self._policy_refs(state)
        timeline = list(state.get("timeline", []))
        timeline.append(
            AgentDecision(
                actor="primary",
                action="APPROVE",
                confidence=0.72,
                reasons=["primary proposes payment only after retrieval and deterministic rule check"],
                policy_refs=refs,
            ).model_dump()
        )
        return {**state, "timeline": timeline}

    def _critic(self, state: AgentGraphState) -> AgentGraphState:
        if state.get("error"):
            return state
        timeline = list(state.get("timeline", []))
        timeline.append(
            AgentDecision(
                actor="critic",
                action="REVIEW",
                confidence=0.78,
                reasons=["critic requires deterministic rules to make the final execution decision"],
                policy_refs=self._policy_refs(state),
            ).model_dump()
        )
        return {**state, "timeline": timeline}

    def _rules(self, state: AgentGraphState) -> AgentGraphState:
        if state.get("error"):
            return self._finalize_review(state, [str(state["error"])], ["FAIL_CLOSED"])
        vendor = Vendor(
            vendor_id=state["vendor_id"],
            status=state.get("vendor_status", "APPROVED"),
            wallet_address=state["vendor_wallet"],
            category=state.get("category", "software"),
            max_single_payment_units=500_000_000,
            wallet_changed_recently=state.get("wallet_changed_recently", False),
        )
        invoice = Invoice(
            invoice_id=state["invoice_id"],
            vendor_id=state["vendor_id"],
            amount_units=state["amount_units"],
            currency="USDC",
            category=state.get("category", "software"),
            recipient_address=state["recipient_address"],
            content_hash=state["invoice_id"],
        )
        result = evaluate_payment(vendor, invoice, paid_invoice_ids=state.get("paid_invoice_ids", set()))
        timeline = list(state.get("timeline", []))
        timeline.append(
            AgentDecision(
                actor="final",
                action=result.decision.value,
                confidence=1.0,
                reasons=result.reasons,
                policy_refs=result.policy_refs or self._policy_refs(state),
            ).model_dump()
        )
        return {
            **state,
            "timeline": timeline,
            "final_action": result.decision.value,
            "rule_codes": result.rule_codes,
        }

    def _human(self, state: AgentGraphState) -> AgentGraphState:
        return state

    def _execute(self, state: AgentGraphState) -> AgentGraphState:
        return state

    def _confirm(self, state: AgentGraphState) -> AgentGraphState:
        return state

    def _route_after_rules(self, state: AgentGraphState) -> str:
        return "execute" if state.get("final_action") == "APPROVE" else "human"

    def _finalize_review(self, state: AgentGraphState, reasons: list[str], refs: list[str]) -> AgentGraphState:
        timeline = list(state.get("timeline", []))
        timeline.append(
            AgentDecision(
                actor="final",
                action="REVIEW",
                confidence=1.0,
                reasons=reasons,
                policy_refs=refs,
            ).model_dump()
        )
        return {**state, "timeline": timeline, "final_action": "REVIEW", "rule_codes": ["FAIL_CLOSED"]}

    @staticmethod
    def _policy_refs(state: AgentGraphState) -> list[str]:
        refs = [
            f"{item.get('document_id', 'policy')}#{item.get('section_id', 'section')}"
            for item in state.get("policy_evidence", [])
        ]
        return refs or ["policy-retrieval#not-configured"]
