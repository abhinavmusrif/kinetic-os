"""Hybrid memory retrieval module."""

from __future__ import annotations

from typing import Any

from memory.scoring import final_score, lexical_overlap, recency_score
from memory.stores.vector_store import VectorStore


class MemoryRetriever:
    """Retrieves relevant memories using hybrid scoring."""

    def __init__(self, memory_manager: Any) -> None:
        self.memory_manager = memory_manager
        self.vector_store = VectorStore()
        self._last_watermark = None

    def _ensure_index(self) -> None:
        beliefs = self.memory_manager.list_beliefs(limit=5000, updated_after=self._last_watermark)
        if not beliefs:
            return
            
        current_watermark = max((b.get("updated_at") or b.get("created_at") for b in beliefs), default=None)
        
        self.vector_store.bulk_add(
            (
                str(item["id"]),
                item["claim"],
                {"type": "belief", "record": item},
            )
            for item in beliefs
        )
        if current_watermark is not None:
            if self._last_watermark is None or current_watermark > self._last_watermark:
                self._last_watermark = current_watermark

    @staticmethod
    def _safe_int(value: object) -> int | None:
        try:
            return int(str(value))
        except Exception:
            return None

    @staticmethod
    def _safe_float(value: object, default: float = 0.0) -> float:
        try:
            return float(str(value))
        except Exception:
            return default

    def retrieve(
        self,
        query: str,
        active_goal: str | None = None,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Return ranked belief records relevant to query."""
        beliefs = self.memory_manager.list_beliefs(limit=500)
        self._ensure_index()
        vector_hits: dict[int, float] = {}
        for hit in self.vector_store.search(query, limit=max(limit * 2, 10)):
            hit_id = self._safe_int(hit.get("id"))
            if hit_id is None:
                continue
            vector_hits[hit_id] = self._safe_float(hit.get("score"), default=0.0)

        scored: list[tuple[float, dict[str, Any]]] = []
        for belief in beliefs:
            belief_id = self._safe_int(belief.get("id"))
            if belief_id is None:
                continue
            lexical = lexical_overlap(query, belief["claim"])
            vector = vector_hits.get(belief_id, 0.0)
            recency = recency_score(belief.get("created_at"))
            confidence = self._safe_float(belief.get("confidence", 0.5), default=0.5)
            goal_rel = lexical_overlap(active_goal or "", belief["claim"]) if active_goal else 0.0
            score = final_score(
                lexical=lexical,
                vector=vector,
                recency=recency,
                confidence=confidence,
                goal_relevance=goal_rel,
            )
            enriched = dict(belief)
            enriched["id"] = belief_id
            enriched["retrieval_score"] = score
            scored.append((score, enriched))
        scored.sort(
            key=lambda pair: (
                pair[0],
                self._safe_float(pair[1].get("confidence", 0.0), default=0.0),
                -int(pair[1]["id"]),
            ),
            reverse=True,
        )
        return [item for _, item in scored[:limit]]
