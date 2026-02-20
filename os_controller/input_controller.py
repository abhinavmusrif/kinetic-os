"""Input controller wrapper for click/type operations via PyAutoGUI."""

from __future__ import annotations

import logging
import os
from typing import Any

if os.name == "nt":
    import ctypes
    try:
        # Prevent Windows from applying DPI virtualization so coordinate mapping matches physical capture.
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

try:
    import pyautogui
    import pyperclip
    # Safety: abort if mouse moves to corners
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.1
except ImportError:
    pyautogui = None
    pyperclip = None


class InputController:
    """Provides high-level keyboard and mouse simulation."""

    def __init__(self) -> None:
        self.logger = logging.getLogger("ao.input_controller")
        if not pyautogui:
            self.logger.warning("pyautogui is not installed. InputController will fail on use.")

    def _check_available(self) -> None:
        if not pyautogui:
            raise RuntimeError("Cannot execute action: pyautogui missing.")

    def move_mouse(self, x: int, y: int) -> str:
        self._check_available()
        pyautogui.moveTo(x, y, duration=0.2)
        return f"Moved mouse to ({x}, {y})"

    def click(self, x: int, y: int) -> str:
        self._check_available()
        pyautogui.click(x=x, y=y, duration=0.2)
        return f"Clicked at ({x}, {y})"

    def double_click(self, x: int, y: int) -> str:
        self._check_available()
        pyautogui.doubleClick(x=x, y=y, duration=0.2)
        return f"Double-clicked at ({x}, {y})"

    def right_click(self, x: int, y: int) -> str:
        self._check_available()
        pyautogui.rightClick(x=x, y=y, duration=0.2)
        return f"Right-clicked at ({x}, {y})"

    def drag(self, x1: int, y1: int, x2: int, y2: int) -> str:
        self._check_available()
        pyautogui.moveTo(x1, y1, duration=0.2)
        pyautogui.dragTo(x2, y2, duration=0.5, button="left")
        return f"Dragged from ({x1}, {y1}) to ({x2}, {y2})"

    def scroll(self, amount: int) -> str:
        self._check_available()
        pyautogui.scroll(amount)
        return f"Scrolled by {amount}"

    def type_text(self, text: str, interval: float = 0.01) -> str:
        self._check_available()
        pyautogui.write(text, interval=interval)
        return f"Typed text of length {len(text)}"

    def press_hotkey(self, *keys: str) -> str:
        self._check_available()
        pyautogui.hotkey(*keys)
        return f"Pressed hotkey: {'+'.join(keys)}"

    def paste_from_clipboard(self, text: str) -> str:
        if not pyperclip or not pyautogui:
            raise RuntimeError("pyperclip or pyautogui missing.")
        pyperclip.copy(text)
        # Assuming Windows
        pyautogui.hotkey("ctrl", "v")
        return f"Pasted text of length {len(text)} from clipboard."
