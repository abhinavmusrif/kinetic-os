"""Semantic memory models."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class SemanticMemory(BaseModel):
    """Belief-level memory with confidence and lifecycle state."""

    claim: str
    confidence: float
    status: str = "proposed"
    supporting_episode_ids: list[int] = Field(default_factory=list)
    conflicts_with_ids: list[int] = Field(default_factory=list)
    last_confirmed_at: datetime | None = None
    scope: str = "global"
