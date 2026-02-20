"""Groq LLM provider (OpenAI-compatible API)."""

from __future__ import annotations

import os
from typing import Any

from llm.base_llm import BaseLLM


class GroqProvider(BaseLLM):
    """Groq inference adapter. Uses OpenAI-compatible endpoint."""

    BASE_URL = "https://api.groq.com/openai/v1"

    def __init__(self, model: str = "llama-3.3-70b-versatile") -> None:
        self.model = model

    def chat(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        _ = kwargs
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            return (
                "Groq provider unavailable: GROQ_API_KEY not set. "
                "Use mock provider or configure credentials."
            )
        try:
            from openai import OpenAI
        except ImportError:
            return (
                "Groq provider unavailable: `openai` package missing. "
                "Install with: pip install openai"
            )
        try:
            client = OpenAI(api_key=api_key, base_url=self.BASE_URL)
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
            )
            content = response.choices[0].message.content
            return content or "Groq returned an empty response."
        except Exception as exc:
            return f"Groq provider failed gracefully: {exc}"
