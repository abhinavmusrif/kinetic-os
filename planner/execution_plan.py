"""Execution plan models."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ExecutionPlan:
    """Simple ordered plan."""

    goal: str
    tasks: list[str] = field(default_factory=list)
