import re

from app.integrations.doubao import PrimaryDecision
from app.services.llm_decisions import _critic_messages, _primary_messages

CJK = re.compile(r"[一-鿿]")


def _primary() -> PrimaryDecision:
    return PrimaryDecision(
        action="HUMAN_REVIEW",
        risk_score=60,
        reasons=["amount requires review"],
        citation_ids=["payment-policy#2.2"],
    )


def test_primary_system_prompt_leads_with_english_rules_and_bilingual_format():
    messages = _primary_messages({}, [])
    system = messages[0]["content"]
    # Decision rules are authored in English, not a Chinese instruction block.
    assert "Rules:" in system
    assert "AUTO_EXECUTE" in system and "HUMAN_REVIEW" in system and "REJECT" in system
    # Format requirement: English first, Chinese in parentheses, with an example.
    assert "English first" in system and "Chinese translation" in system
    assert CJK.search(system), "system prompt must carry a bilingual example"


def test_critic_system_prompt_leads_with_english_rules_and_bilingual_format():
    messages = _critic_messages({}, _primary(), [])
    system = messages[0]["content"]
    assert "blocking_issues" in system
    assert "English first" in system and "Chinese translation" in system
    assert CJK.search(system), "system prompt must carry a bilingual example"


def test_prompt_examples_are_bilingual():
    primary_user = _primary_messages({}, [])[1]["content"]
    assert "金额" in primary_user and "amount requires review" in primary_user
    critic_user = _critic_messages({}, _primary(), [])[1]["content"]
    assert "金额" in critic_user and "amount requires review" in critic_user
