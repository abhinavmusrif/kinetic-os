"""Linux OS controller."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any

from os_controller.base_controller import BaseController, TaskResult
from vision.screen_capture import capture_screen


class LinuxController(BaseController):
    """Linux controller with safe best-effort behavior."""

    def __init__(self, allow_os_automation: bool = False) -> None:
        self.allow_os_automation = allow_os_automation

    def _ensure_allowed(self) -> None:
        if not self.allow_os_automation:
            raise RuntimeError("Disabled by governance")
        if os.name != "posix":
            raise RuntimeError("Linux controller inactive on non-posix platform.")

    def open_app(self, app_name: str) -> str:
        self._ensure_allowed()
        try:
            subprocess.Popen([app_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return f"Attempted to open app: {app_name}"
        except Exception as exc:
            return f"Failed to open app '{app_name}': {exc}"

    def click(self, x: int, y: int) -> str:
        self._ensure_allowed()
        return f"Click not executed on Linux controller without automation backend ({x}, {y})."

    def type_text(self, text: str) -> str:
        self._ensure_allowed()
        return f"Type text request received (not executed): {text[:100]}"

    def capture_screen(self, output_path: Path) -> Path:
        self._ensure_allowed()
        captured = capture_screen(output_path=output_path)
        if captured is None:
            raise RuntimeError("Screen capture unavailable on this Linux environment.")
        return captured

    def get_active_window(self) -> dict[str, Any]:
        self._ensure_allowed()
        return {"title": "unknown", "pid": None, "platform": "linux"}

    def list_windows(self) -> list[dict[str, Any]]:
        self._ensure_allowed()
        return []

    def execute_task(self, task: dict[str, Any]) -> TaskResult:
        self._ensure_allowed()
        return {
            "success": False,
            "steps": ["Linux controller does not support structured OS tasks."],
            "last_hash": None,
            "reason": "UNSUPPORTED"
        }
