"""Task dependency graph scaffold."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class DependencyGraph:
    """Represents dependencies among tasks."""

    nodes: list[str] = field(default_factory=list)
    edges: list[tuple[str, str]] = field(default_factory=list)
