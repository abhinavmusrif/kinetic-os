"""Goal memory models."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field


class GoalMemory(BaseModel):
    """Active goal record."""

    goal_text: str
    priority: int = 5
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    deadline: datetime | None = None
    progress_state: str = "active"
    subgoals: list[str] = Field(default_factory=list)
    completion_criteria: str = ""
