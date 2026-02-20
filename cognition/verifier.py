"""Verification helper for outputs."""

from __future__ import annotations


def verify(statement: str) -> float:
    """Return a rough confidence estimate for a statement."""
    if not statement.strip():
        return 0.0
    if "likely" in statement.lower():
        return 0.7
    return 0.8
