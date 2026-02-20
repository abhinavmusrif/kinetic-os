"""Context memory models."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field


class ContextMessage(BaseModel):
    """Single message in context buffer."""

    role: str
    content: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
