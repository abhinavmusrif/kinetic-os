"""Safety gates for learning updates."""

from __future__ import annotations


def allow_learning_update(risk_score: float) -> bool:
    """Only allow learning updates for low-risk operations."""
    return risk_score <= 0.3
