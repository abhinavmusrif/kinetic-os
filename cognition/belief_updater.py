"""Belief update helper utilities."""

from __future__ import annotations


def propose_belief(text: str, confidence: float) -> dict[str, object]:
    """Create a normalized belief proposal payload."""
    return {
        "claim": text,
        "confidence": max(0.0, min(1.0, confidence)),
        "status": "proposed",
    }
