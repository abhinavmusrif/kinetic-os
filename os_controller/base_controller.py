"""Base interface for OS automation controllers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, TypedDict


class TaskResult(TypedDict):
    success: bool
    steps: list[str]
    last_hash: str | None
    reason: str | None



class BaseController(ABC):
    """Abstract automation controller interface."""

    @abstractmethod
    def open_app(self, app_name: str) -> str:
        """Open an application."""
        pass

    @abstractmethod
    def click(self, x: int, y: int) -> str:
        """Perform click action."""
        pass

    @abstractmethod
    def type_text(self, text: str) -> str:
        """Type text into active input."""
        pass

    @abstractmethod
    def capture_screen(self, output_path: Path) -> Path:
        """Capture screen to file."""
        pass

    @abstractmethod
    def get_active_window(self) -> dict[str, Any]:
        """Return active window metadata."""
        pass

    @abstractmethod
    def list_windows(self) -> list[dict[str, Any]]:
        """Return visible windows list."""
        pass

    @abstractmethod
    def execute_task(self, task: dict[str, Any]) -> TaskResult:
        """Execute a structured OS task."""
        pass
