"""Uncertainty ledger models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class HypothesisMemory(BaseModel):
    """Hypothesis tracked with verification plan."""

    hypothesis: str
    what_would_verify: str
    evidence: list[str] = Field(default_factory=list)
    risk_if_wrong: str
    next_verification_action: str
    confidence: float = 0.5
