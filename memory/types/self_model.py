"""Self-model memory models."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field


class SelfModelMemory(BaseModel):
    """Agent self-model with capabilities and reliability."""

    tools_available: list[str] = Field(default_factory=list)
    capabilities: str = ""
    limitations: str = ""
    reliability_scores: dict[str, float] = Field(default_factory=dict)
    last_updated: datetime = Field(default_factory=lambda: datetime.now(UTC))
