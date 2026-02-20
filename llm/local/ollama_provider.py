"""Ollama provider adapter."""

from __future__ import annotations

import json
import subprocess
from typing import Any

from llm.base_llm import BaseLLM


class OllamaProvider(BaseLLM):
    """Very small Ollama adapter that checks availability before use."""

    def __init__(self, model: str = "llama3.1") -> None:
        self.model = model

    @staticmethod
    def is_available() -> bool:
        try:
            subprocess.run(
                ["ollama", "--version"],
                check=True,
                capture_output=True,
                text=True,
            )
            return True
        except Exception:
            return False

    def chat(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        _ = kwargs
        if not self.is_available():
            return "Ollama unavailable: binary not found. Falling back recommended."
        prompt = messages[-1]["content"] if messages else ""
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
        }
        try:
            proc = subprocess.run(
                ["ollama", "chat", "--json"],
                input=json.dumps(payload),
                capture_output=True,
                text=True,
                check=True,
            )
        except Exception as exc:  # pragma: no cover - external binary path
            return f"Ollama call failed gracefully: {exc}"
        text = proc.stdout.strip()
        if not text:
            return f"Ollama returned no text for prompt: {prompt[:80]}"
        return text
