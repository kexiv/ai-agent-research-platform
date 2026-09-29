import json
from typing import Any

import httpx

from app.config import get_settings


class LLMError(RuntimeError):
    """Raised when the configured OpenAI-compatible endpoint cannot answer."""


class OpenAICompatibleClient:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def chat(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.0,
        json_mode: bool = False,
    ) -> str:
        if not self.settings.llm_enabled:
            raise LLMError("OPENAI_API_KEY is not configured")

        payload: dict[str, Any] = {
            "model": self.settings.openai_model,
            "messages": messages,
            "temperature": temperature,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        headers = {
            "Authorization": f"Bearer {self.settings.openai_api_key}",
            "Content-Type": "application/json",
        }
        url = f"{self.settings.openai_base_url.rstrip('/')}/chat/completions"

        async with httpx.AsyncClient(timeout=45.0) as client:
            response = await client.post(url, headers=headers, json=payload)
        if response.is_error:
            raise LLMError(f"LLM request failed: {response.status_code} {response.text[:300]}")

        body = response.json()
        try:
            return str(body["choices"][0]["message"]["content"])
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError(f"Unexpected LLM response: {json.dumps(body)[:500]}") from exc
