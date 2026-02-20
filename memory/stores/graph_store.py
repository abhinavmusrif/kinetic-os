"""Graph store for relationship memory."""

from __future__ import annotations


class GraphStore:
    """Minimal in-memory graph relationship store."""

    def __init__(self) -> None:
        self.edges: list[tuple[str, str, str]] = []

    def add_edge(self, source: str, relation: str, target: str) -> None:
        self.edges.append((source, relation, target))
