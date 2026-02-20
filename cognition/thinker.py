"""Reasoning helper for candidate next actions."""

from __future__ import annotations


def think(goal: str) -> str:
    """Return a compact thought string for a goal."""
    return f"Focus on safe progress toward: {goal}"
