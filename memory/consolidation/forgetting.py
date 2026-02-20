"""Retention and forgetting policies."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from memory.schemas import BeliefRecord, EpisodeRecord


class ForgettingPolicy:
    """Applies confidence decay and episode pruning under retention policy."""

    def __init__(self, memory_manager: Any) -> None:
        self.memory_manager = memory_manager

    def run(self, retention_days: int = 30) -> dict[str, int]:
        """Decay stale beliefs and prune low-salience old episodes."""
        cutoff = datetime.now(UTC) - timedelta(days=retention_days)
        decayed = 0
        pruned = 0

        with self.memory_manager.sql_store.session() as sess:
            stale_beliefs = (
                sess.query(BeliefRecord)
                .filter(BeliefRecord.created_at < cutoff)
                .filter(BeliefRecord.status == "proposed")
                .all()
            )
            for belief in stale_beliefs:
                belief.confidence = max(0.1, belief.confidence * 0.95)
                decayed += 1

            old_episodes = (
                sess.query(EpisodeRecord)
                .filter(EpisodeRecord.timestamp < cutoff)
                .filter(EpisodeRecord.confidence < 0.4)
                .all()
            )
            for episode in old_episodes:
                # Evidence references are preserved in dedicated evidence table.
                sess.delete(episode)
                pruned += 1

        return {"decayed_beliefs": decayed, "pruned_episodes": pruned}
