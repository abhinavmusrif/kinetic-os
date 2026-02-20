"""Google Gemini LLM provider with exponential backoff.

Uses the google-genai SDK to call Gemini models.  Includes robust rate-limit
handling: on 429 / quota errors, retries up to 5 times with exponential
backoff (2s → 4s → 8s → 16s → 32s).
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any

from llm.base_llm import BaseLLM

logger = logging.getLogger("ao.llm.gemini")

_MAX_RETRIES = 5
_BASE_WAIT_SECONDS = 2.0


class GeminiProvider(BaseLLM):
    """Google Gemini API adapter with exponential backoff on rate limits."""

    def __init__(self, model: str = "gemini-2.5-flash") -> None:
        self.model = model

    def chat(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        _ = kwargs
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return (
                "Gemini provider unavailable: GEMINI_API_KEY not set. "
                "Use mock provider or configure credentials."
            )
        try:
            from google import genai
        except ImportError:
            return (
                "Gemini provider unavailable: `google-genai` package missing. "
                "Install with: pip install google-genai"
            )

        client = genai.Client(api_key=api_key)
        contents = self._convert_messages(messages)

        # ── Exponential backoff loop ──────────────────────────────────
        last_error: Exception | None = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                response = client.models.generate_content(
                    model=self.model,
                    contents=contents,
                )
                return response.text or "Gemini returned an empty response."

            except Exception as exc:
                last_error = exc
                exc_str = str(exc).lower()

                # Check if this is a rate-limit / quota error worth retrying
                is_rate_limit = any(
                    keyword in exc_str
                    for keyword in ("429", "rate limit", "quota", "resource exhausted", "too many")
                )

                if not is_rate_limit:
                    # Non-retryable error — fail immediately
                    logger.error("Gemini call failed (non-retryable): %s", exc)
                    return f"Gemini provider failed gracefully: {exc}"

                # Rate limit hit — exponential backoff
                wait = _BASE_WAIT_SECONDS * (2 ** (attempt - 1))
                logger.warning(
                    "Gemini rate limit hit (attempt %d/%d). "
                    "Waiting %.1fs before retry... Error: %s",
                    attempt,
                    _MAX_RETRIES,
                    wait,
                    exc,
                )
                time.sleep(wait)

        # All retries exhausted
        logger.error(
            "Gemini provider exhausted %d retries. Last error: %s",
            _MAX_RETRIES,
            last_error,
        )
        return f"Gemini provider failed after {_MAX_RETRIES} retries: {last_error}"

    @staticmethod
    def _convert_messages(messages: list[dict[str, str]]) -> list[dict[str, Any]]:
        """Convert OpenAI-style messages to Gemini contents format."""
        contents: list[dict[str, Any]] = []
        system_text = ""

        for msg in messages:
            role = msg.get("role", "user")
            text = msg.get("content", "")

            if role == "system":
                system_text = text
                continue

            gemini_role = "model" if role == "assistant" else "user"
            contents.append({
                "role": gemini_role,
                "parts": [{"text": text}],
            })

        # Prepend system instruction to first user message if present
        if system_text and contents:
            first = contents[0]
            if first["role"] == "user":
                original_text = first["parts"][0]["text"]
                first["parts"][0]["text"] = f"[System: {system_text}]\n\n{original_text}"

        return contents
