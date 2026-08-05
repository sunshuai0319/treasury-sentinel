import asyncio
from functools import lru_cache
from typing import Any, Literal, Protocol

from app.config import Settings, get_settings
from app.integrations.doubao import CriticDecision, DoubaoClient, PrimaryDecision


class LlmDecisionProvider(Protocol):
    def primary(self, state: dict[str, Any], policy_refs: list[str]) -> PrimaryDecision: ...

    def critic(
        self, state: dict[str, Any], primary: PrimaryDecision, policy_refs: list[str]
    ) -> CriticDecision: ...


class DoubaoDecisionProvider:
    def __init__(
        self,
        client: DoubaoClient,
        primary_temperature: float,
        critic_temperature: float,
        primary_max_tokens: int,
        critic_max_tokens: int,
    ):
        self.client = client
        self.primary_temperature = primary_temperature
        self.critic_temperature = critic_temperature
        self.primary_max_tokens = primary_max_tokens
        self.critic_max_tokens = critic_max_tokens

    def primary(self, state: dict[str, Any], policy_refs: list[str]) -> PrimaryDecision:
        return _run_coro(
            self.client.structured_chat(
                _primary_messages(state, policy_refs),
                PrimaryDecision,
                self.primary_temperature,
                max_tokens=self.primary_max_tokens,
            )
        )[0]

    def critic(
        self, state: dict[str, Any], primary: PrimaryDecision, policy_refs: list[str]
    ) -> CriticDecision:
        return _run_coro(
            self.client.structured_chat(
                _critic_messages(state, primary, policy_refs),
                CriticDecision,
                self.critic_temperature,
                max_tokens=self.critic_max_tokens,
            )
        )[0]


@lru_cache(maxsize=1)
def get_live_llm_decision_provider() -> LlmDecisionProvider:
    settings = get_settings()
    return build_live_llm_decision_provider(settings)


def build_live_llm_decision_provider(settings: Settings) -> LlmDecisionProvider:
    return DoubaoDecisionProvider(
        DoubaoClient(
            settings.ark_api_key,
            settings.ark_base_url,
            settings.doubao_model,
            settings.doubao_timeout_seconds,
        ),
        settings.doubao_primary_temperature,
        settings.doubao_critic_temperature,
        settings.doubao_primary_max_tokens,
        settings.doubao_critic_max_tokens,
    )


def primary_action_to_timeline(action: Literal["AUTO_EXECUTE", "HUMAN_REVIEW", "REJECT"]):
    if action == "AUTO_EXECUTE":
        return "APPROVE"
    if action == "HUMAN_REVIEW":
        return "REVIEW"
    return "REJECT"


def critic_action_to_timeline(action: Literal["AUTO_EXECUTE", "HUMAN_REVIEW", "REJECT"]):
    if action == "AUTO_EXECUTE":
        return "APPROVE"
    if action == "HUMAN_REVIEW":
        return "REVIEW"
    return "REJECT"


def _run_coro(coro):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    coro.close()
    raise RuntimeError("DoubaoDecisionProvider cannot run inside an active event loop")


def _primary_messages(state: dict[str, Any], policy_refs: list[str]) -> list[dict[str, str]]:
    context = _llm_context(state, policy_refs)
    return [
        {
            "role": "system",
            "content": (
                '只输出一行JSON。字段固定为 action,risk_score,reasons,citation_ids。'
                'action只能是AUTO_EXECUTE,HUMAN_REVIEW,REJECT。'
                '规则：vendor_status不是APPROVED或地址不匹配或近期换地址=>REJECT；'
                'amount_units<=500000000且供应商已批准且地址匹配=>AUTO_EXECUTE；'
                '其他=>HUMAN_REVIEW。'
            ),
        },
        {
            "role": "user",
            "content": (
                f"amount_units={context['amount_units']};"
                f"vendor_status={context['vendor_status']};"
                f"vendor_wallet={context['vendor_wallet']};"
                f"recipient_address={context['recipient_address']};"
                f"wallet_changed_recently={context['wallet_changed_recently']};"
                f"policy_refs={','.join(policy_refs[:3])}. "
                '返回示例：{"action":"HUMAN_REVIEW","risk_score":60,'
                '"reasons":["amount requires review"],"citation_ids":["payment-policy#2.2"]}'
            ),
        },
    ]


def _critic_messages(
    state: dict[str, Any], primary: PrimaryDecision, policy_refs: list[str]
) -> list[dict[str, str]]:
    context = _llm_context(state, policy_refs)
    return [
        {
            "role": "system",
            "content": (
                '只输出一行JSON。字段固定为 challenge,blocking_issues,recommended_action。'
                '只能保持或升级风险，不能把HUMAN_REVIEW/REJECT降为AUTO_EXECUTE。'
                '如地址不匹配、供应商未批准、近期换地址=>REJECT；'
                '如金额超过500000000=>HUMAN_REVIEW；否则沿用primary。'
            ),
        },
        {
            "role": "user",
            "content": (
                f"amount_units={context['amount_units']};"
                f"vendor_status={context['vendor_status']};"
                f"vendor_wallet={context['vendor_wallet']};"
                f"recipient_address={context['recipient_address']};"
                f"wallet_changed_recently={context['wallet_changed_recently']};"
                f"primary={primary.model_dump_json()}. "
                '返回示例：{"challenge":true,"blocking_issues":["amount requires review"],'
                '"recommended_action":"HUMAN_REVIEW"}'
            ),
        },
    ]


def _llm_context(state: dict[str, Any], policy_refs: list[str]) -> dict[str, Any]:
    return {
        "request_id": state.get("request_id"),
        "invoice_id": state.get("invoice_id"),
        "vendor_id": state.get("vendor_id"),
        "amount_units": state.get("amount_units"),
        "vendor_status": state.get("vendor_status"),
        "vendor_wallet": state.get("vendor_wallet"),
        "recipient_address": state.get("recipient_address"),
        "category": state.get("category"),
        "wallet_changed_recently": state.get("wallet_changed_recently"),
        "policy_refs": policy_refs,
        "policy_evidence": [_compact_evidence(item) for item in state.get("policy_evidence", [])[:3]],
    }


def _compact_evidence(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "document_id": item.get("document_id"),
        "section_id": item.get("section_id"),
        "title": item.get("title"),
        "score": item.get("score"),
    }
