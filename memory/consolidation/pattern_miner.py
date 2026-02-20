"""Pattern miner."""

from __future__ import annotations

from typing import Any


class PatternMiner:
    """Extracts trivial recurring tags from episodes."""

    def mine(self, episodes: list[dict[str, Any]]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for episode in episodes:
            for tag in episode.get("tags", []):
                counts[tag] = counts.get(tag, 0) + 1
        return counts
