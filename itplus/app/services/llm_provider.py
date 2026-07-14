"""Multi-driver LLM provider (OpenAI-compatible API)."""

from __future__ import annotations

import logging
from typing import Any

from openai import OpenAI

from itplus.app.core.config import get_settings

logger = logging.getLogger(__name__)


class LLMProvider:
    """Unified interface for groq, openai, and ollama drivers."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self._client: OpenAI | None = None

    @property
    def client(self) -> OpenAI:
        if self._client is None:
            base_url = self.settings.ai_base_url
            api_key = self.settings.ai_api_key or "not-needed"

            if self.settings.ai_driver == "ollama":
                base_url = base_url or "http://localhost:11434/v1"
                api_key = "ollama"

            self._client = OpenAI(base_url=base_url, api_key=api_key)
        return self._client

    def chat_completion(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        model: str | None = None,
    ) -> str:
        temperature = temperature if temperature is not None else self.settings.ai_temperature
        max_tokens = max_tokens if max_tokens is not None else self.settings.ai_max_tokens
        model = model or self.settings.ai_model

        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            content = response.choices[0].message.content
            return content or ""
        except Exception as exc:
            logger.error("LLM completion failed (driver=%s): %s", self.settings.ai_driver, exc)
            raise

    def chat_completion_stream(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        model: str | None = None,
    ):
        temperature = temperature if temperature is not None else self.settings.ai_temperature
        max_tokens = max_tokens if max_tokens is not None else self.settings.ai_max_tokens
        model = model or self.settings.ai_model

        stream = self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

    def get_model_name(self) -> str:
        return self.settings.ai_model


llm_provider = LLMProvider()
