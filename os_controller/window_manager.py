"""Window manager for active/list window calls via PyGetWindow."""

from __future__ import annotations

import logging
from typing import Any

try:
    import pygetwindow as gw
except ImportError:
    gw = None


class WindowManager:
    """Facade for managing desktop windows on Windows."""

    def __init__(self) -> None:
        self.logger = logging.getLogger("ao.window_manager")
        if not gw:
            self.logger.warning("pygetwindow is not installed.")

    def _check_available(self) -> None:
        if not gw:
            raise RuntimeError("Cannot execute window operation: pygetwindow missing.")

    def get_active_window(self) -> dict[str, Any] | None:
        self._check_available()
        try:
            window = gw.getActiveWindow()
            if not window:
                return None
            return {
                "title": window.title,
                "bbox": [window.left, window.top, window.right, window.bottom],
                "is_maximized": window.isMaximized,
            }
        except Exception as e:
            self.logger.warning("Failed to get active window: %s", e)
            return None

    def list_windows(self) -> list[dict[str, Any]]:
        self._check_available()
        try:
            windows = gw.getAllWindows()
            return [
                {
                    "title": w.title,
                    "bbox": [w.left, w.top, w.right, w.bottom],
                    "is_active": w.isActive,
                }
                for w in windows if w.title.strip()
            ]
        except Exception as e:
            self.logger.warning("Failed to list windows: %s", e)
            return []

    def focus_window(self, title_substring: str) -> bool:
        self._check_available()
        try:
            windows = gw.getWindowsWithTitle(title_substring)
            if not windows:
                return False
            window = windows[0]
            if not window.isActive:
                window.activate()
            return True
        except Exception as e:
            self.logger.warning("Failed to focus window containing '%s': %s", title_substring, e)
            return False

    def bring_to_front(self, title_substring: str) -> bool:
        """Alias for focus_window for compatibility."""
        return self.focus_window(title_substring)
