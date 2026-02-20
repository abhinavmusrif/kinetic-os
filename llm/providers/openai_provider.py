"""OpenAI provider with graceful fallback behavior."""

from __future__ import annotations

import os
from typing import Any

from llm.base_llm import BaseLLM


class OpenAIProvider(BaseLLM):
    """OpenAI API adapter. Works only when dependency and API key are present."""

    def __init__(self, model: str = "gpt-4o-mini") -> None:
        self.model = model

    def chat(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        _ = kwargs
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return (
                "OpenAI provider unavailable: OPENAI_API_KEY not set. "
                "Use mock provider or configure credentials."
            )
        try:
            from openai import OpenAI
        except Exception:
            return (
                "OpenAI provider unavailable: `openai` package missing. "
                "Install optional dependency or switch provider."
            )
        try:
            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(model=self.model, messages=messages)
            content = response.choices[0].message.content
            return content or "OpenAI returned an empty response."
        except Exception as exc:  # pragma: no cover - external API path
            return f"OpenAI provider failed gracefully: {exc}"
