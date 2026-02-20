"""Uncertainty reasoning helpers."""

from __future__ import annotations


def uncertainty_from_confidence(confidence: float) -> float:
    """Map confidence to uncertainty."""
    return max(0.0, min(1.0, 1.0 - confidence))
