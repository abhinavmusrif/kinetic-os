"""Simple self-critique utility."""

from __future__ import annotations


def critique(result: str) -> str:
    """Return a lightweight critique label."""
    if "failed" in result.lower():
        return "needs_revision"
    return "acceptable"
