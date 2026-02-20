"""Windows automation controller orchestrating visual perception and action."""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from typing import Any

from os_controller.base_controller import BaseController, TaskResult
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

    def _ensure_focus(self, target_window_title: str) -> bool:
        if not target_window_title:
            return True
        return self.window_manager.focus_window(target_window_title)

    def _dismiss_common_popups(self) -> None:
        self.input_controller.press_hotkey("esc")
        time.sleep(0.5)

    def _scroll_search(self, direction: int = -1) -> None:
        self.input_controller.scroll(amount=500 * direction)
        time.sleep(1.0)

    def execute_task(self, task: dict[str, Any]) -> TaskResult:
        """Execute a highly reliable operator task with progression tracking."""
        self._ensure_allowed()
        
        action = task.get("action")
        steps_log: list[str] = []
        last_hash: str | None = None
        
        # We can implement a larger loop for complex tasks, or handle specific primitives.
        if action == "open_app":
            name = task.get("name", "")
            out = self.open_app(name)
            steps_log.append(out)
            return {"success": True, "steps": steps_log, "last_hash": None, "reason": None}
            
        elif action == "hotkey":
            keys = task.get("keys", [])
            self.input_controller.press_hotkey(*keys)
            steps_log.append(f"Pressed hotkey {keys}")
            time.sleep(1.0)
            return {"success": True, "steps": steps_log, "last_hash": None, "reason": None}
            
        elif action == "wait":
            secs = task.get("seconds", 1.0)
            time.sleep(secs)
            steps_log.append(f"Waited {secs}s")
            return {"success": True, "steps": steps_log, "last_hash": None, "reason": None}

        elif action == "direct_type":
            # Type directly into the currently focused window — no visual targeting needed
            text = task.get("text", "")
            self.input_controller.safe_type(text)
            steps_log.append(f"Typed '{text}' into active window")
            time.sleep(0.5)
            return {"success": True, "steps": steps_log, "last_hash": None, "reason": None}

        elif action == "direct_save_as":
            # Save via Ctrl+S → type filepath → Enter, no visual targeting
            filepath = task.get("filepath", "")
            self.input_controller.press_hotkey("ctrl", "shift", "s")
            time.sleep(1.5)
            # Clear existing filename field & type new path
            self.input_controller.press_hotkey("ctrl", "a")
            time.sleep(0.3)
            self.input_controller.safe_type(filepath)
            time.sleep(0.5)
            self.input_controller.press_hotkey("enter")
            time.sleep(1.0)
            # Handle "already exists" confirmation if it pops up
            self.input_controller.press_hotkey("left")
            time.sleep(0.3)
            self.input_controller.press_hotkey("enter")
            time.sleep(0.5)
            steps_log.append(f"Saved file as '{filepath}'")
            return {"success": True, "steps": steps_log, "last_hash": None, "reason": None}
            
        elif action in ("click", "type", "assert"):
            max_attempts = task.get("max_attempts", 3)
            same_hash_count = 0
            
            for attempt in range(max_attempts):
                steps_log.append(f"Attempt {attempt+1}/{max_attempts}")
                
                # 1. Capture Before
                cap_before = self.screen_capture.capture_screen()
                if not cap_before:
                    steps_log.append("Failed to capture screen.")
                    return {"success": False, "steps": steps_log, "last_hash": last_hash, "reason": "CAPTURE_FAILED"}
                
                current_hash = cap_before["hash"]
                if current_hash == last_hash:
                    same_hash_count += 1
                    if same_hash_count >= 3:
                        steps_log.append("No progress detected. Screen stuck.")
                        return {"success": False, "steps": steps_log, "last_hash": current_hash, "reason": "NO_PROGRESS"}
                else:
                    same_hash_count = 0
                
                last_hash = current_hash
                
                # target processing
                target_info = task.get("target", {})
                
                # Locate target (Stub for structured locator strategy that will be expanded in next task)
                # Strategy: UIA -> Visual -> OCR
                
                # For now, reuse old visual approach if target is text
                text_target = target_info.get("text") or task.get("target_label")
                target_el = None
                
                if text_target:
                    analysis = self.screen_reader.analyze(cap_before, prompt=f"Find '{text_target}'")
                    for el in analysis.get("elements", []):
                        if text_target.lower() in el.get("label", "").lower():
                            target_el = el
                            break
                
                if not target_el:
                    steps_log.append(f"Target '{text_target}' not found.")
                    self._scroll_search()
                    continue
                
                bbox = target_el["bbox"]
                cx = int((bbox[0] + bbox[2]) / 2)
                cy = int((bbox[1] + bbox[3]) / 2)
                
                # Execute action
                if action == "click":
                    self.input_controller.click(cx, cy)
                elif action == "type":
                    self.input_controller.click(cx, cy)
                    time.sleep(0.5)
                    self.input_controller.type_text(task.get("text", ""))
                
                time.sleep(1.0)
                
                # Verify
                cap_after = self.screen_capture.capture_screen()
                if cap_after and cap_after["hash"] != current_hash:
                    steps_log.append("State changed visually. Success.")
                    return {"success": True, "steps": steps_log, "last_hash": cap_after["hash"], "reason": None}
                
                steps_log.append("State did not change. Retrying.")
                self._dismiss_common_popups()
            
            return {"success": False, "steps": steps_log, "last_hash": last_hash, "reason": "MAX_ATTEMPTS_EXCEEDED"}

        return {"success": False, "steps": steps_log, "last_hash": None, "reason": "UNRECOGNIZED_ACTION"}
