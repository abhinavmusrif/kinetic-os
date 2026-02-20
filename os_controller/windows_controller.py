"""Windows automation controller orchestrating visual perception and action."""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from typing import Any

from os_controller.base_controller import BaseController
from os_controller.input_controller import InputController
from os_controller.screen_capture import ScreenCapture
from os_controller.screen_reader import ScreenReader
from os_controller.window_manager import WindowManager


class WindowsController(BaseController):
    """Windows controller that actively perceives and controls the desktop."""

    def __init__(self, allow_os_automation: bool = False, vision_router: Any | None = None) -> None:
        self.allow_os_automation = allow_os_automation
        self.logger = logging.getLogger("ao.windows_controller")

        if allow_os_automation and os.name != "nt":
            self.logger.warning("Windows controller should only be run on Windows.")
            self.allow_os_automation = False

        self.input_controller = InputController()
        self.window_manager = WindowManager()
        self.screen_capture = ScreenCapture()
        self.screen_reader = ScreenReader(vision_router=vision_router)

    def _ensure_allowed(self) -> None:
        if not self.allow_os_automation:
            raise RuntimeError("OS Automation is disabled by governance configuration.")
        if os.name != "nt":
            raise RuntimeError("Windows controller requires a Windows environment.")

    def open_app(self, app_name: str) -> str:
        """Open an application safely."""
        self._ensure_allowed()
        self.input_controller.press_hotkey("win")
        time.sleep(0.5)
        self.input_controller.type_text(app_name)
        time.sleep(0.5)
        self.input_controller.press_hotkey("enter")
        time.sleep(2.0)
        return f"Attempted to open '{app_name}' via start menu."

    def click(self, x: int, y: int) -> str:
        self._ensure_allowed()
        return self.input_controller.click(x, y)

    def type_text(self, text: str) -> str:
        self._ensure_allowed()
        return self.input_controller.type_text(text)

    def capture_screen(self, output_path: Path) -> Path:
        self._ensure_allowed()
        capture = self.screen_capture.capture_screen()
        if not capture:
            raise RuntimeError("Screen capture unavailable.")
        capture["image"].save(output_path)
        return output_path

    def get_active_window(self) -> dict[str, Any]:
        self._ensure_allowed()
        win = self.window_manager.get_active_window()
        return win if win else {"title": "unknown", "pid": None}

    def list_windows(self) -> list[dict[str, Any]]:
        self._ensure_allowed()
        return self.window_manager.list_windows()

    def execute_visual_action(self, goal_description: str, target_label: str, action: str = "click", text_to_type: str = "") -> bool:
        """Perception-action-verification loop to interact with the GUI visually."""
        self._ensure_allowed()
        max_attempts = 3
        
        for attempt in range(max_attempts):
            self.logger.info("Visual action attempt %d/%d for goal: %s", attempt + 1, max_attempts, goal_description)
            
            capture = self.screen_capture.capture_screen()
            if not capture:
                self.logger.error("Failed to capture screen.")
                time.sleep(1)
                continue

            analysis = self.screen_reader.analyze(capture, prompt=f"Find the UI element for '{target_label}' to reach goal: '{goal_description}'")
            
            target_el = None
            for el in analysis.get("elements", []):
                if target_label.lower() in el.get("label", "").lower():
                    target_el = el
                    break

            if not target_el:
                self.logger.warning("Target '%s' not found. State: %s", target_label, analysis.get("state_summary"))
                time.sleep(1)
                continue

            bbox = target_el["bbox"]
            center_x = int((bbox[0] + bbox[2]) / 2)
            center_y = int((bbox[1] + bbox[3]) / 2)
            
            if center_x < 0 or center_y < 0 or center_x > capture["resolution"][0] or center_y > capture["resolution"][1]:
                self.logger.error("Computed coordinates out of bounds. Aborting.")
                return False

            if action == "click":
                self.input_controller.click(center_x, center_y)
            elif action == "type":
                self.input_controller.click(center_x, center_y)
                time.sleep(0.1)
                self.input_controller.type_text(text_to_type)
            elif action == "double_click":
                self.input_controller.double_click(center_x, center_y)

            time.sleep(1.0)

            post_capture = self.screen_capture.capture_screen()
            if not post_capture:
                continue

            # Verification based on frame hash diff
            if capture["hash"] != post_capture["hash"]:
                self.logger.info("Screen state changed after action. Verification success.")
                return True
            else:
                self.logger.warning("Screen hash unchanged. Action might have failed.")
        
        return False
