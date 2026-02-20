"""Optional vector store with FAISS and pure-Python fallback."""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Iterable


def _tokenize(text: str) -> list[str]:
    return [t for t in "".join(ch.lower() if ch.isalnum() else " " for ch in text).split() if t]


def _sparse_embedding(text: str) -> Counter[str]:
    return Counter(_tokenize(text))


def _cosine_sparse(a: Counter[str], b: Counter[str]) -> float:
    keys = set(a.keys()) | set(b.keys())
    dot = sum(a.get(k, 0) * b.get(k, 0) for k in keys)
    norm_a = math.sqrt(sum(v * v for v in a.values()))
    norm_b = math.sqrt(sum(v * v for v in b.values()))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class VectorStore:
    """In-memory vector similarity index with optional FAISS."""

    def __init__(self) -> None:
        self._items: dict[str, tuple[dict[str, object], Counter[str]]] = {}
        self._faiss = None
        try:
            import faiss

            self._faiss = faiss
        except Exception:
            self._faiss = None

    def add(self, item_id: str, text: str, payload: dict[str, object]) -> None:
        """Add or update item in fallback index."""
        self._items[item_id] = (payload, _sparse_embedding(text))

    def search(self, query: str, limit: int = 5) -> list[dict[str, object]]:
        """Search similar items using cosine over sparse embeddings."""
        query_emb = _sparse_embedding(query)
        scored: list[tuple[float, str, dict[str, object]]] = []
        for item_id, (payload, emb) in self._items.items():
            score = _cosine_sparse(query_emb, emb)
            scored.append((score, item_id, payload))
        scored.sort(key=lambda x: x[0], reverse=True)
        results: list[dict[str, object]] = []
        for score, item_id, payload in scored[:limit]:
            results.append({"id": item_id, "score": score, "payload": payload})
        return results

    def bulk_add(
        self,
        rows: Iterable[tuple[str, str, dict[str, object]]],
    ) -> None:
        """Add many rows."""
        for item_id, text, payload in rows:
            self.add(item_id=item_id, text=text, payload=payload)
