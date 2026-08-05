import pytest

from app.integrations.doubao import (
    CriticDecision,
    DoubaoClient,
    PrimaryDecision,
    critic_final_action,
)


class FakeDoubaoClient(DoubaoClient):
    def __init__(self, responses: list[dict]):
        super().__init__("test-key", "https://example.invalid", "doubao-test", 1.0)
        self.responses = responses

    async def chat_json(self, messages, temperature=0.1, max_tokens=256):
        return self.responses.pop(0)


def completion(content: str) -> dict:
    return {
        "id": "req_1",
        "model": "doubao-test",
        "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        "choices": [{"message": {"content": content}}],
    }


@pytest.mark.asyncio
async def test_structured_chat_retries_once_after_schema_error():
    client = FakeDoubaoClient(
        [
            completion('{"action":"AUTO_EXECUTE","risk_score":120,"reasons":[],"citation_ids":[]}'),
            completion(
                '{"action":"AUTO_EXECUTE","risk_score":15,'
                '"reasons":["policy allows"],"citation_ids":["payment-policy#2.1"]}'
            ),
        ]
    )

    decision, metadata = await client.structured_chat([], PrimaryDecision)

    assert decision.action == "AUTO_EXECUTE"
    assert decision.risk_score == 15
    assert metadata.request_id == "req_1"
    assert metadata.prompt_tokens == 10


def test_critic_cannot_downgrade_human_review_to_auto_execute():
    primary = PrimaryDecision(
        action="HUMAN_REVIEW",
        risk_score=64,
        reasons=["wallet recently changed"],
        citation_ids=["wallet-change-policy#1.1"],
    )
    critic = CriticDecision(
        challenge=False,
        blocking_issues=[],
        recommended_action="AUTO_EXECUTE",
    )

    assert critic_final_action(primary, critic) == "REVIEW"
