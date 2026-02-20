"""Human-kinematics input controller — mouse, keyboard, and scroll simulation.

All mouse movements use quadratic Bezier curves with ease-in/ease-out timing,
micro-hesitations before clicks, and occasional overshoots to produce motion
indistinguishable from a real human operator.
"""

from __future__ import annotations

import logging
import math
import os
import random
import time
from typing import Any

if os.name == "nt":
    import ctypes

    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

try:
    import pyautogui
    import pyperclip

    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.02  # Lower base pause; we handle timing ourselves
except ImportError:
    pyautogui = None
    pyperclip = None


# ---------------------------------------------------------------------------
# Bezier math helpers (no external deps beyond stdlib)
# ---------------------------------------------------------------------------

def _lerp(a: float, b: float, t: float) -> float:
    """Linear interpolation."""
    return a + (b - a) * t


def _quadratic_bezier(
    p0: tuple[float, float],
    p1: tuple[float, float],
    p2: tuple[float, float],
    t: float,
) -> tuple[float, float]:
    """Evaluate a quadratic Bezier curve at parameter t ∈ [0, 1]."""
    x = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t ** 2 * p2[0]
    y = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t ** 2 * p2[1]
    return (x, y)


def _ease_in_out(t: float) -> float:
    """Smooth ease-in / ease-out (cubic hermite)."""
    if t < 0.5:
        return 4 * t * t * t
    return 1 - (-2 * t + 2) ** 3 / 2


def _generate_control_point(
    start: tuple[int, int], end: tuple[int, int]
) -> tuple[float, float]:
    """Generate a random control point to create a natural arc."""
    mx = (start[0] + end[0]) / 2
    my = (start[1] + end[1]) / 2
    dist = math.hypot(end[0] - start[0], end[1] - start[1])
    # Arc magnitude: 10-30% of distance, random direction
    offset = dist * random.uniform(0.10, 0.30)
    angle = random.uniform(0, 2 * math.pi)
    cx = mx + offset * math.cos(angle)
    cy = my + offset * math.sin(angle)
    return (cx, cy)


class InputController:
    """Human-like keyboard and mouse simulation with natural kinematics."""

    def __init__(self) -> None:
        self.logger = logging.getLogger("ao.input_controller")
        if not pyautogui:
            self.logger.warning("pyautogui not installed. InputController disabled.")

    def _check_available(self) -> None:
        if not pyautogui:
            raise RuntimeError("Cannot execute action: pyautogui missing.")

    # ------------------------------------------------------------------
    # Human-like mouse movement
    # ------------------------------------------------------------------

    def human_move_to(self, x: int, y: int, duration: float | None = None) -> str:
        """Move the mouse along a Bezier curve with ease-in/ease-out timing.

        - Generates a quadratic Bezier arc (not a straight line).
        - Uses cubic-hermite easing for natural acceleration/deceleration.
        - Occasionally overshoots and corrects.
        """
        self._check_available()
        start = pyautogui.position()
        sx, sy = int(start[0]), int(start[1])
        dist = math.hypot(x - sx, y - sy)

        if dist < 3:
            # Already there
            pyautogui.moveTo(x, y)
            return f"Already near ({x}, {y})"

        # Duration scales with distance: ~0.3s for short, ~0.9s for long moves
        if duration is None:
            duration = min(0.9, max(0.25, dist / 1200)) + random.uniform(-0.05, 0.08)

        # Generate Bezier control point for natural arc
        control = _generate_control_point((sx, sy), (x, y))
        p0 = (float(sx), float(sy))
        p2 = (float(x), float(y))

        # Number of steps scales with distance
        steps = max(15, min(80, int(dist / 8)))
        dt = duration / steps

        for i in range(1, steps + 1):
            t_raw = i / steps
            t_eased = _ease_in_out(t_raw)
            bx, by = _quadratic_bezier(p0, control, p2, t_eased)
            pyautogui.moveTo(int(bx), int(by), _pause=False)
            # Variable inter-step delay for natural feel
            time.sleep(dt * random.uniform(0.7, 1.3))

        # --- Occasional overshoot (20% chance) ---
        if random.random() < 0.20:
            self._do_overshoot(x, y)

        # Ensure we land exactly on target
        pyautogui.moveTo(x, y, _pause=False)
        return f"Human-moved to ({x}, {y})"

    def _do_overshoot(self, target_x: int, target_y: int) -> None:
        """Simulate an overshoot: miss by 2-5px, pause, then correct."""
        ox = target_x + random.randint(-5, 5)
        oy = target_y + random.randint(-5, 5)
        # Clamp so we never go off-screen
        screen_w, screen_h = pyautogui.size()
        ox = max(0, min(screen_w - 1, ox))
        oy = max(0, min(screen_h - 1, oy))
        pyautogui.moveTo(ox, oy, _pause=False)
        time.sleep(random.uniform(0.05, 0.12))  # Brief pause at wrong spot
        # Correct back with a small movement
        steps = random.randint(3, 6)
        for i in range(1, steps + 1):
            t = i / steps
            cx = int(_lerp(ox, target_x, _ease_in_out(t)))
            cy = int(_lerp(oy, target_y, _ease_in_out(t)))
            pyautogui.moveTo(cx, cy, _pause=False)
            time.sleep(random.uniform(0.01, 0.025))

    def _micro_hesitate(self) -> None:
        """Pause 150-400ms before a click, simulating visual confirmation."""
        time.sleep(random.uniform(0.15, 0.40))

    # ------------------------------------------------------------------
    # Mouse actions (all use human-like movement)
    # ------------------------------------------------------------------

    def move_mouse(self, x: int, y: int) -> str:
        return self.human_move_to(x, y)

    def click(self, x: int, y: int) -> str:
        self._check_available()
        self.human_move_to(x, y)
        self._micro_hesitate()
        pyautogui.click(_pause=False)
        return f"Clicked at ({x}, {y})"

    def double_click(self, x: int, y: int) -> str:
        self._check_available()
        self.human_move_to(x, y)
        self._micro_hesitate()
        pyautogui.doubleClick(_pause=False)
        return f"Double-clicked at ({x}, {y})"

    def human_safe_click(self, x: int, y: int) -> str:
        """Click with slight jitter — extra-human for sensitive targets."""
        self._check_available()
        jx = x + random.randint(-2, 2)
        jy = y + random.randint(-2, 2)
        self.human_move_to(jx, jy)
        self._micro_hesitate()
        pyautogui.click(_pause=False)
        return f"Human-safe clicked at ({jx}, {jy})"

    def right_click(self, x: int, y: int) -> str:
        self._check_available()
        self.human_move_to(x, y)
        self._micro_hesitate()
        pyautogui.rightClick(_pause=False)
        return f"Right-clicked at ({x}, {y})"

    def drag(self, x1: int, y1: int, x2: int, y2: int) -> str:
        self._check_available()
        self.human_move_to(x1, y1)
        self._micro_hesitate()
        # Drag uses its own Bezier path
        control = _generate_control_point((x1, y1), (x2, y2))
        dist = math.hypot(x2 - x1, y2 - y1)
        duration = min(1.2, max(0.4, dist / 800))
        steps = max(15, int(dist / 10))
        dt = duration / steps

        pyautogui.mouseDown(_pause=False)
        for i in range(1, steps + 1):
            t = _ease_in_out(i / steps)
            bx, by = _quadratic_bezier(
                (float(x1), float(y1)), control, (float(x2), float(y2)), t
            )
            pyautogui.moveTo(int(bx), int(by), _pause=False)
            time.sleep(dt * random.uniform(0.8, 1.2))
        pyautogui.mouseUp(_pause=False)
        return f"Dragged from ({x1}, {y1}) to ({x2}, {y2})"

    # ------------------------------------------------------------------
    # Human-like scrolling
    # ------------------------------------------------------------------

    def scroll(self, amount: int) -> str:
        """Scroll with staggered, human-rhythm chunks."""
        self._check_available()
        return self.human_scroll(amount)

    def human_scroll(self, total_clicks: int) -> str:
        """Scroll in staggered chunks with variable pauses, like a human reading.

        Humans scroll in bursts (2-5 ticks), pause to read (200-600ms),
        then continue. Scroll direction is preserved from the sign of total_clicks.
        """
        self._check_available()
        direction = 1 if total_clicks > 0 else -1
        remaining = abs(total_clicks)

        while remaining > 0:
            # Random chunk size: 1-5 scroll ticks
            chunk = min(remaining, random.randint(1, 5))
            pyautogui.scroll(chunk * direction, _pause=False)
            remaining -= chunk

            if remaining > 0:
                # Simulate "reading" pause between scroll bursts
                time.sleep(random.uniform(0.20, 0.60))

        return f"Human-scrolled {total_clicks} clicks"

    # ------------------------------------------------------------------
    # Keyboard
    # ------------------------------------------------------------------

    def type_text(self, text: str, interval: float = 0.01) -> str:
        """Type text character by character with slight randomized intervals."""
        self._check_available()
        for char in text:
            pyautogui.write(char, interval=0, _pause=False)
            # Human-like typing: variable delay per character
            time.sleep(interval + random.uniform(0.005, 0.035))
        return f"Typed text of length {len(text)}"

    def safe_type(self, text: str) -> str:
        """Type using clipboard paste for long strings, direct input for short."""
        self._check_available()
        if len(text) > 20 and pyperclip:
            return self.paste_from_clipboard(text)
        return self.type_text(text, interval=0.02)

    def press_hotkey(self, *keys: str) -> str:
        self._check_available()
        pyautogui.hotkey(*keys, _pause=False)
        return f"Pressed hotkey: {'+'.join(keys)}"

    def paste_from_clipboard(self, text: str) -> str:
        if not pyperclip or not pyautogui:
            raise RuntimeError("pyperclip or pyautogui missing.")
        pyperclip.copy(text)
        pyautogui.hotkey("ctrl", "v", _pause=False)
        # Small delay after paste to let UI process
        time.sleep(random.uniform(0.1, 0.2))
        return f"Pasted text of length {len(text)} from clipboard."
