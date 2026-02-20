"""Episodic memory models."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field


class EpisodicMemory(BaseModel):
    """Event-like memory record."""

    event_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    summary: str
    raw_context_refs: list[str] = Field(default_factory=list)
    actions_taken: list[str] = Field(default_factory=list)
    outcome: str
    evidence_refs: list[str] = Field(default_factory=list)
    confidence: float = 0.5
    tags: list[str] = Field(default_factory=list)
    privacy_level: str = "internal"
