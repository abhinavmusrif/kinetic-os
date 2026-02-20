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
        claims = self.memory_manager.list_semantic_claims(limit=5000)
        episodes = self.memory_manager.list_episodes(limit=1000)
        procedures = self.memory_manager.list_procedures(limit=500)
        
        payloads: list[tuple[str, str, dict[str, Any]]] = []
        for c in claims:
            payloads.append((f"claim_{c['id']}", c["claim"], {"type": "claim", "record": c}))
        for e in episodes:
            text = f"{e.get('summary', '')} {e.get('text', '')}"
            payloads.append((f"episode_{e['id']}", text, {"type": "episode", "record": e}))
        for p in procedures:
            text = f"{p.get('name', '')} {p.get('trigger_pattern', '')}"
            payloads.append((f"procedure_{p['id']}", text, {"type": "procedure", "record": p}))

        self.vector_store.bulk_add(payloads)

    @staticmethod
    def _safe_float(value: object, default: float = 0.0) -> float:
        try:
            return float(str(value))
        except Exception:
            return default

    def retrieve(
        self,
        query: str,
        k: int = 10,
        mode: str = "hybrid",
        active_goal: str | None = None,
    ) -> dict[str, list[dict[str, Any]]]:
        """Return ranked distinct records relevant to query."""
        self._ensure_index()
        
        # We search for k * 3 to ensure we have enough pool for lexical rescoring if mode=="hybrid"
        vector_hits = self.vector_store.search(query, limit=max(k * 3, 20))
        
        scored: list[tuple[float, dict[str, Any]]] = []
        for hit in vector_hits:
            hit_id = str(hit.get("id"))
            vec_score = self._safe_float(hit.get("score"), default=0.0)
            payload = hit.get("payload", {})
            record_type = payload.get("type", "unknown")
            record = payload.get("record", {})
            
            # Determine lexical text
            lex_text = ""
            conf = 0.5
            if record_type == "claim":
                lex_text = record.get("claim", "")
                conf = self._safe_float(record.get("confidence", 0.5))
            elif record_type == "episode":
                lex_text = f"{record.get('summary', '')} {record.get('text', '')}"
                conf = self._safe_float(record.get("confidence", 1.0))
            elif record_type == "procedure":
                lex_text = f"{record.get('name', '')} {record.get('trigger_pattern', '')}"
                conf = self._safe_float(record.get("success_rate", 1.0))

            lexical = lexical_overlap(query, lex_text) if mode == "hybrid" else 0.0
            recency = recency_score(record.get("created_at") or record.get("timestamp"))
            goal_rel = lexical_overlap(active_goal or "", lex_text) if active_goal else 0.0
            
            score = final_score(
                lexical=lexical,
                vector=vec_score,
                recency=recency,
                confidence=conf,
                goal_relevance=goal_rel,
            )
            
            enriched = dict(record)
            enriched["retrieval_score"] = score
            enriched["retrieval_type"] = record_type
            scored.append((score, enriched))
            
        scored.sort(
            key=lambda pair: (
                pair[0],
                self._safe_float(pair[1].get("confidence", pair[1].get("success_rate", 0.0))),
            ),
            reverse=True,
        )
        
        results_by_type: dict[str, list[dict[str, Any]]] = {
            "episodes": [],
            "claims": [],
            "procedures": [],
        }
        
        for i in range(min(k, len(scored))):
            _, item = scored[i]
            rtype = item.pop("retrieval_type")
            if rtype == "claim":
                results_by_type["claims"].append(item)
            elif rtype == "episode":
                results_by_type["episodes"].append(item)
            elif rtype == "procedure":
                results_by_type["procedures"].append(item)
                
        return results_by_type
