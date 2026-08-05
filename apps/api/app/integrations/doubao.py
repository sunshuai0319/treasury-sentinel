import json
import time
from dataclasses import dataclass
from typing import Any, Literal, TypeVar

import httpx
from pydantic import BaseModel, Field, ValidationError


class PrimaryDecision(BaseModel):
    action: Literal["AUTO_EXECUTE", "HUMAN_REVIEW", "REJECT"]
    risk_score: int = Field(ge=0, le=100)
    reasons: list[str]
    citation_ids: list[str]


class CriticDecision(BaseModel):
    challenge: bool
    blocking_issues: list[str]
    recommended_action: Literal["AUTO_EXECUTE", "HUMAN_REVIEW", "REJECT"]


@dataclass(frozen=True)
class DoubaoCallMetadata:
    model: str
    request_id: str | None
    elapsed_ms: int
    prompt_tokens: int | None
    completion_tokens: int | None


TDecision = TypeVar("TDecision", bound=BaseModel)


class DoubaoClient:
    def __init__(self, api_key: str, base_url: str, model: str):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def chat_json(self, messages: list[dict[str, str]], temperature: float = 0.1) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "response_format": {"type": "json_object"},
        }
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(f"{self.base_url}/chat/completions", json=payload, headers=headers)
            response.raise_for_status()
            return response.json()

    async def structured_chat(
        self,
        messages: list[dict[str, str]],
        schema: type[TDecision],
        temperature: float = 0.1,
    ) -> tuple[TDecision, DoubaoCallMetadata]:
        last_error: ValidationError | json.JSONDecodeError | KeyError | TypeError | None = None
        started = time.perf_counter()
        data: dict[str, Any] = {}
        for attempt in range(2):
            request_messages = messages
            if attempt:
                request_messages = [
                    *messages,
                    {
                        "role": "user",
                        "content": (
                            "Previous response did not match the required JSON schema. "
                            "Return only one JSON object with the exact required fields."
                        ),
                    },
                ]
            data = await self.chat_json(request_messages, temperature)
            try:
                content = data["choices"][0]["message"]["content"]
                parsed = json.loads(content) if isinstance(content, str) else content
                decision = schema.model_validate(parsed)
                return decision, self._metadata(data, started)
            except (ValidationError, json.JSONDecodeError, KeyError, TypeError) as exc:
                last_error = exc
        raise ValueError(f"Doubao response failed schema validation: {last_error}")

    @staticmethod
    def _metadata(data: dict[str, Any], started: float) -> DoubaoCallMetadata:
        usage = data.get("usage") or {}
        return DoubaoCallMetadata(
            model=str(data.get("model") or ""),
            request_id=data.get("id"),
            elapsed_ms=int((time.perf_counter() - started) * 1000),
            prompt_tokens=usage.get("prompt_tokens"),
            completion_tokens=usage.get("completion_tokens"),
        )


def critic_final_action(primary: PrimaryDecision, critic: CriticDecision) -> Literal["APPROVE", "REVIEW", "REJECT"]:
    if primary.action == "REJECT" or critic.recommended_action == "REJECT":
        return "REJECT"
    if primary.action == "HUMAN_REVIEW" or critic.challenge or critic.recommended_action == "HUMAN_REVIEW":
        return "REVIEW"
    return "APPROVE"
