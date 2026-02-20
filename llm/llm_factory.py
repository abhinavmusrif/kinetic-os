"""LLM provider factory."""

from __future__ import annotations

from typing import Any

from llm.base_llm import BaseLLM
from llm.local.ollama_provider import OllamaProvider
from llm.providers.gemini_provider import GeminiProvider
from llm.providers.groq_provider import GroqProvider
from llm.providers.mock_provider import MockProvider
from llm.providers.openai_provider import OpenAIProvider


def build_llm(config: dict[str, Any]) -> BaseLLM:
    """Build an LLM provider from configuration, defaulting safely to mock."""
    models_cfg = config.get("models", {}).get("llm", {})
    active = models_cfg.get("active_provider", "mock")
    providers = models_cfg.get("providers", {})
    active_cfg = providers.get(active, {})
    provider_type = active_cfg.get("type", active)

    if provider_type == "openai":
        return OpenAIProvider(model=active_cfg.get("model", "gpt-4o-mini"))
    if provider_type == "gemini":
        return GeminiProvider(model=active_cfg.get("model", "gemini-2.5-flash"))
    if provider_type == "groq":
        return GroqProvider(model=active_cfg.get("model", "llama-3.3-70b-versatile"))
    if provider_type == "ollama":
        return OllamaProvider(model=active_cfg.get("model", "llama3.1"))
    return MockProvider()
