"""OpenAI LLM provider. Real implementation, used when OPENAI_API_KEY is set."""
from __future__ import annotations
from typing import Iterable

import httpx

from app.config import settings
from app.providers.base import ProviderError
from app.providers.llm.base import LLMMessage, LLMProvider, LLMResponse


class OpenAILLMProvider(LLMProvider):
    name = "openai"

    def __init__(self, api_key: str | None = None, model: str | None = None,
                 base_url: str | None = None) -> None:
        self.api_key = api_key or settings.llm_api_key
        self.model = model or settings.llm_model
        self.base_url = (base_url or settings.llm_base_url or "https://api.openai.com/v1").rstrip("/")
        if not self.api_key:
            raise ProviderError(
                "OpenAI LLM is not configured. Set LLM_API_KEY in your environment."
            )
        self._client = httpx.AsyncClient(timeout=60.0)

    async def chat(
        self,
        messages: Iterable[LLMMessage],
        *,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        response_format_json: bool = False,
    ) -> LLMResponse:
        body = {
            "model": self.model,
            "messages": [m.__dict__ for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format_json:
            body["response_format"] = {"type": "json_object"}

        r = await self._client.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json=body,
        )
        if r.status_code != 200:
            raise ProviderError(
                f"OpenAI returned {r.status_code}: {r.text[:200]}"
            )
        data = r.json()
        return LLMResponse(
            content=data["choices"][0]["message"]["content"],
            model=data.get("model"),
            usage=data.get("usage"),
            raw=data,
        )

    async def close(self) -> None:
        await self._client.aclose()
