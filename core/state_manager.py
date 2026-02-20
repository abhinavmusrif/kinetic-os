"""Runtime state container for lightweight orchestration state."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RuntimeState:
    """Mutable in-memory state for a single run/session."""

    active_goal: str | None = None
    last_plan: list[str] = field(default_factory=list)
    last_actions: list[dict[str, Any]] = field(default_factory=list)
    last_observation: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class StateManager:
    """Wraps runtime state and provides convenience update methods."""

    def __init__(self) -> None:
        self.state = RuntimeState()

    def set_goal(self, goal: str) -> None:
        self.state.active_goal = goal

    def set_plan(self, plan: list[str]) -> None:
        self.state.last_plan = plan

    def add_action(self, action: dict[str, Any]) -> None:
        self.state.last_actions.append(action)

    def set_observation(self, observation: str) -> None:
        self.state.last_observation = observation
