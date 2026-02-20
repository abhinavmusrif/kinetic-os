"""Desktop state schema."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class DesktopState:
    """Minimal desktop snapshot."""

    open_windows: list[str] = field(default_factory=list)
    active_window: str | None = None
