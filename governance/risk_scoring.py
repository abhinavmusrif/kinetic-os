"""Heuristic risk scoring for actions."""

from __future__ import annotations

from typing import Any


def score_action_risk(action: str, tool_name: str, payload: dict[str, Any] | None = None) -> float:
    """Return risk score in [0, 1] based on action/tool heuristics."""
    payload = payload or {}
    action_l = action.lower()
    tool_l = tool_name.lower()

    risk = 0.05
    if "delete" in action_l or "delete" in str(payload).lower():
        risk = max(risk, 0.85)
    if "shell" in tool_l:
        risk = max(risk, 0.8)
    if "browser" in tool_l:
        risk = max(risk, 0.65)
    if "git" in tool_l and any(word in action_l for word in ["reset", "clean", "rebase"]):
        risk = max(risk, 0.9)
    if "payment" in action_l or "login" in action_l:
        risk = max(risk, 0.95)
    if "mock" in tool_l:
        risk = min(risk, 0.1)
    return max(0.0, min(1.0, risk))
