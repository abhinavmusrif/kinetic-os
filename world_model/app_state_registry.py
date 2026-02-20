"""Registry for known application states."""

from __future__ import annotations

from typing import Any


class AppStateRegistry:
    """Tracks app-level state snapshots."""

    def __init__(self) -> None:
        self._apps: dict[str, dict[str, Any]] = {}

    def register(self, app_name: str, state: dict[str, Any]) -> None:
        self._apps[app_name] = state

    def get(self, app_name: str) -> dict[str, Any] | None:
        return self._apps.get(app_name)

    def all(self) -> dict[str, dict[str, Any]]:
        return dict(self._apps)
