"""Native GUI browser controller — no Playwright/Selenium/WebDriver.

Uses the OS controller to interact with the user's native browser through
physical mouse movements and keyboard input, making all actions
indistinguishable from a real human operator.
"""

from __future__ import annotations

import logging
import os
import subprocess
import time
from pathlib import Path
from typing import Any

from tools.base_tool import BaseTool

logger = logging.getLogger("ao.browser_controller")


class BrowserControllerTool(BaseTool):
    """Browser automation via native OS input — no WebDriver, no bot fingerprint.

    How it works:
    - Opens the user's default browser via ``os.startfile`` / ``subprocess``.
    - Waits for the browser window to appear via ``window_manager``.
    - Uses ``input_controller.human_move_to`` for all mouse actions.
    - Uses native hotkeys (Ctrl+L, Ctrl+T, etc.) for browser chrome interaction.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._os_controller: Any | None = None

    def _get_os_controller(self) -> Any:
        """Lazily build the OS controller (avoids import at module level)."""
        if self._os_controller is None:
            from os_controller.windows_controller import WindowsController

            self._os_controller = WindowsController(allow_os_automation=True)
        return self._os_controller

    def metadata(self, payload: dict[str, object]) -> dict[str, object]:
        _ = payload
        return {"requires_network": True}

    def _run(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Route browser commands through native OS input."""
        task_raw = payload.get("task", "")

        if isinstance(task_raw, str):
            return self._handle_task_string(task_raw)
        return {"outcome": "No actionable browser task provided.", "success": False}

    def _handle_task_string(self, task: str) -> dict[str, Any]:
        """Parse natural-language browser task and execute via native OS."""
        import re

        task_l = task.lower().strip()
        task_clean = re.sub(r"^task:\s*", "", task, flags=re.IGNORECASE).strip()

        # --- Navigate to URL ---
        url_match = re.search(
            r"(?:go\s+to|navigate\s+to|open|visit|browse\s+to)\s+(https?://\S+|www\.\S+|\S+\.\w{2,})",
            task_clean,
            flags=re.IGNORECASE,
        )
        if url_match:
            url = url_match.group(1)
            if not url.startswith("http"):
                url = "https://" + url
            return self._navigate_to_url(url)

        # --- Search the web ---
        search_match = re.search(
            r"(?:search\s+(?:for\s+)?|google\s+)(.+)",
            task_clean,
            flags=re.IGNORECASE,
        )
        if search_match:
            query = search_match.group(1).strip().strip("'\"")
            return self._search_web(query)

        # --- Open new tab ---
        if "new tab" in task_l:
            return self._new_tab()

        # --- Close tab ---
        if "close tab" in task_l:
            return self._close_tab()

        # --- Refresh page ---
        if "refresh" in task_l or "reload" in task_l:
            return self._refresh_page()

        # --- Go back ---
        if "go back" in task_l or "back" in task_l:
            return self._go_back()

        # --- Scroll down ---
        if "scroll down" in task_l:
            return self._scroll_page(direction="down")

        # --- Scroll up ---
        if "scroll up" in task_l:
            return self._scroll_page(direction="up")

        # --- Fallback: try to treat entire task as a URL or search ---
        if "." in task_clean and " " not in task_clean:
            url = task_clean if task_clean.startswith("http") else "https://" + task_clean
            return self._navigate_to_url(url)

        return {
            "outcome": f"Browser task not recognized: {task}",
            "success": False,
            "confidence": 0.3,
        }

    # ------------------------------------------------------------------
    # Core browser actions (all via native OS input)
    # ------------------------------------------------------------------

    def _navigate_to_url(self, url: str) -> dict[str, Any]:
        """Navigate to a URL using the native browser."""
        steps: list[str] = []

        # 1. Open default browser if no browser window is detected
        ctl = self._get_os_controller()
        browser_window = self._find_browser_window(ctl)

        if not browser_window:
            steps.append("No browser window found. Launching default browser...")
            self._launch_default_browser()
            time.sleep(2.5)
            # Re-check for browser window
            browser_window = self._find_browser_window(ctl)
            if not browser_window:
                # Last resort: just open the URL directly
                self._open_url_via_os(url)
                steps.append(f"Opened URL via OS default handler: {url}")
                return {"outcome": "\n".join(steps), "success": True, "confidence": 0.8}

        # 2. Focus the browser window
        if browser_window:
            title = browser_window.get("title", "")
            ctl.window_manager.focus_window(title)
            steps.append(f"Focused browser window: {title}")
            time.sleep(0.5)

        # 3. Focus the address bar with Ctrl+L
        ctl.input_controller.press_hotkey("ctrl", "l")
        steps.append("Focused address bar (Ctrl+L)")
        time.sleep(0.5)

        # 4. Select all existing text and type the URL
        ctl.input_controller.press_hotkey("ctrl", "a")
        time.sleep(0.2)
        ctl.input_controller.safe_type(url)
        steps.append(f"Typed URL: {url}")
        time.sleep(0.3)

        # 5. Press Enter to navigate
        ctl.input_controller.press_hotkey("enter")
        steps.append("Pressed Enter to navigate")
        time.sleep(2.0)

        return {
            "outcome": f"Navigated to {url}\nSteps: {steps}",
            "success": True,
            "confidence": 0.9,
            "evidence_refs": [],
        }

    def _search_web(self, query: str) -> dict[str, Any]:
        """Search the web via the browser address bar."""
        ctl = self._get_os_controller()
        steps: list[str] = []

        browser_window = self._find_browser_window(ctl)
        if not browser_window:
            self._launch_default_browser()
            time.sleep(2.5)

        # Focus address bar, type search query
        ctl.input_controller.press_hotkey("ctrl", "l")
        time.sleep(0.5)
        ctl.input_controller.press_hotkey("ctrl", "a")
        time.sleep(0.2)
        ctl.input_controller.safe_type(query)
        steps.append(f"Typed search query: {query}")
        time.sleep(0.3)

        ctl.input_controller.press_hotkey("enter")
        steps.append("Pressed Enter to search")
        time.sleep(2.0)

        return {
            "outcome": f"Searched for: {query}\nSteps: {steps}",
            "success": True,
            "confidence": 0.85,
            "evidence_refs": [],
        }

    def _new_tab(self) -> dict[str, Any]:
        ctl = self._get_os_controller()
        ctl.input_controller.press_hotkey("ctrl", "t")
        time.sleep(0.8)
        return {"outcome": "Opened new browser tab (Ctrl+T)", "success": True, "confidence": 0.95}

    def _close_tab(self) -> dict[str, Any]:
        ctl = self._get_os_controller()
        ctl.input_controller.press_hotkey("ctrl", "w")
        time.sleep(0.5)
        return {"outcome": "Closed current tab (Ctrl+W)", "success": True, "confidence": 0.95}

    def _refresh_page(self) -> dict[str, Any]:
        ctl = self._get_os_controller()
        ctl.input_controller.press_hotkey("f5")
        time.sleep(1.5)
        return {"outcome": "Refreshed page (F5)", "success": True, "confidence": 0.95}

    def _go_back(self) -> dict[str, Any]:
        ctl = self._get_os_controller()
        ctl.input_controller.press_hotkey("alt", "left")
        time.sleep(1.0)
        return {"outcome": "Navigated back (Alt+Left)", "success": True, "confidence": 0.95}

    def _scroll_page(self, direction: str = "down") -> dict[str, Any]:
        ctl = self._get_os_controller()
        clicks = -5 if direction == "down" else 5
        ctl.input_controller.human_scroll(clicks)
        return {
            "outcome": f"Scrolled {direction} on page",
            "success": True,
            "confidence": 0.9,
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _find_browser_window(ctl: Any) -> dict[str, Any] | None:
        """Find an open browser window by checking window titles."""
        browser_keywords = ["chrome", "edge", "firefox", "brave", "opera", "vivaldi", "browser"]
        try:
            windows = ctl.window_manager.list_windows()
            for win in windows:
                title = win.get("title", "").lower()
                if any(kw in title for kw in browser_keywords):
                    return win
        except Exception:
            pass
        return None

    @staticmethod
    def _launch_default_browser() -> None:
        """Launch the system's default web browser."""
        if os.name == "nt":
            try:
                os.startfile("http://")
            except Exception:
                subprocess.Popen(["start", "http://"], shell=True)
        else:
            subprocess.Popen(["xdg-open", "http://"])

    @staticmethod
    def _open_url_via_os(url: str) -> None:
        """Open a specific URL using the OS default handler."""
        if os.name == "nt":
            try:
                os.startfile(url)
            except Exception:
                subprocess.Popen(["start", url], shell=True)
        else:
            subprocess.Popen(["xdg-open", url])
