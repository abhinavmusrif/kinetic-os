"""Base interface for OS automation controllers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class BaseController(ABC):
    """Abstract automation controller interface."""

    @abstractmethod
    def open_app(self, app_name: str) -> str:
        """Open an application."""

    @abstractmethod
    def click(self, x: int, y: int) -> str:
        """Perform click action."""

    @abstractmethod
    def type_text(self, text: str) -> str:
        """Type text into active input."""

    @abstractmethod
    def capture_screen(self, output_path: Path) -> Path:
        """Capture screen to file."""

    @abstractmethod
    def get_active_window(self) -> dict[str, Any]:
        """Return active window metadata."""

    @abstractmethod
    def list_windows(self) -> list[dict[str, Any]]:
        """Return visible windows list."""
