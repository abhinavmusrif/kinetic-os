"""Scoring helpers for memory retrieval."""

from __future__ import annotations

from datetime import UTC, datetime


def lexical_overlap(query: str, text: str) -> float:
    """Compute simple token overlap ratio."""
    q_tokens = {token.lower() for token in query.split() if token.strip()}
    t_tokens = {token.lower() for token in text.split() if token.strip()}
    if not q_tokens or not t_tokens:
        return 0.0
    return len(q_tokens & t_tokens) / len(q_tokens)


def recency_score(timestamp: datetime | None) -> float:
    """Map record recency to [0,1]."""
    if timestamp is None:
        return 0.5
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=UTC)
    now = datetime.now(UTC)
    age_days = max(0.0, (now - timestamp).total_seconds() / 86400.0)
    return max(0.0, 1.0 - min(1.0, age_days / 30.0))


def final_score(
    lexical: float,
    vector: float,
    recency: float,
    confidence: float,
    goal_relevance: float,
) -> float:
    """Weighted retrieval score."""
    return (
        0.15 * lexical + 0.05 * vector + 0.35 * recency + 0.40 * confidence + 0.05 * goal_relevance
    )
