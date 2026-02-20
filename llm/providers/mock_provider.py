"""Deterministic local fallback LLM provider for offline usage."""

from __future__ import annotations

import re
from collections import Counter

from llm.base_llm import BaseLLM


class MockProvider(BaseLLM):
    """Rule-based local responder when external LLM backends are unavailable."""

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        return [token for token in re.split(r"[^a-zA-Z0-9]+", text.lower()) if token]

    @staticmethod
    def _summarize_tokens(tokens: list[str], max_items: int = 8) -> str:
        if not tokens:
            return "no salient terms detected"
        top = Counter(tokens).most_common(max_items)
        return ", ".join(term for term, _ in top)

    def _decompose(self, prompt: str) -> str:
        cleaned = prompt.strip()
        parts = [
            p.strip() for p in re.split(r"\band\b|,|;", cleaned, flags=re.IGNORECASE) if p.strip()
        ]
        if not parts:
            parts = [cleaned]
        lines = [f"{idx}. {part}" for idx, part in enumerate(parts, start=1)]
        return "\n".join(lines[:5])

    def chat(self, messages: list[dict[str, str]], **kwargs: object) -> str:
        """Generate deterministic text from conversational messages."""
        _ = kwargs
        if not messages:
            return "No input received."
        user_messages = [m["content"] for m in messages if m.get("role") == "user"]
        prompt = user_messages[-1] if user_messages else messages[-1]["content"]

        if "decompose" in prompt.lower():
            return self._decompose(prompt)

        remember_match = re.search(
            r"remember\s+i\s+love\s+([a-zA-Z0-9\-\s]+)", prompt, flags=re.IGNORECASE
        )
        if remember_match:
            item = remember_match.group(1).strip().rstrip(".")
            return (
                f"I noted a likely preference: user likes {item}. "
                "I will store it as a proposed belief."
            )
        salient = self._summarize_tokens(self._tokenize(prompt))
        return f"Local fallback response. Salient terms: {salient}."
