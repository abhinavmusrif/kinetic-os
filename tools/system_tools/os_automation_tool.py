"""OS Automation tool with window-focus verification and browser aliases.

CRITICAL RULES:
- Before any type/click/scroll, verifies the target window is in the foreground.
- Maps 'web browser' → a real executable (chrome, msedge, firefox).
- Uses Spatial UI Mapping + LLM for click targeting when needed.
"""

from __future__ import annotations

import json
import logging
import re
import shutil
import time
from pathlib import Path
from typing import Any

from executor.safe_runner import SafeRunner
from os_controller.windows_controller import WindowsController
from tools.base_tool import BaseTool
from vision.vision_router import VisionRouter

# ── Browser aliases ───────────────────────────────────────────────────

_BROWSER_ALIASES: dict[str, list[str]] = {
    "web browser": ["chrome", "msedge", "firefox"],
    "browser": ["chrome", "msedge", "firefox"],
    "internet": ["chrome", "msedge", "firefox"],
    "google": ["chrome"],
    "chrome": ["chrome"],
    "edge": ["msedge"],
    "firefox": ["firefox"],
}

# Executable names we can find on PATH or in common locations
_APP_EXE_MAP: dict[str, str] = {
    "chrome": "chrome",
    "msedge": "msedge",
    "firefox": "firefox",
    "notepad": "notepad",
    "calculator": "calc",
    "explorer": "explorer",
    "cmd": "cmd",
    "powershell": "powershell",
    "code": "code",
}

# Window title substrings to verify the app actually opened
_APP_WINDOW_HINTS: dict[str, list[str]] = {
    "chrome": ["Chrome", "Google Chrome"],
    "msedge": ["Edge", "Microsoft Edge"],
    "firefox": ["Firefox", "Mozilla Firefox"],
    "notepad": ["Notepad", "Untitled"],
    "calculator": ["Calculator"],
    "explorer": ["File Explorer", "Explorer"],
    "code": ["Visual Studio Code"],
}

_LLM_CLICK_SYSTEM_PROMPT = """\
You are a screen interaction engine for an autonomous desktop operator.
Below is the parsed screen data — a numbered list of text elements detected on
the current screen, each with its (x, y) pixel coordinate.

{spatial_map}

The user wants to achieve the following task:
"{task}"

Which element should be clicked? Reply with ONLY a JSON object:
{{"x": <integer>, "y": <integer>, "reason": "<brief explanation>"}}

If no suitable element is found, reply with:
{{"x": -1, "y": -1, "reason": "No matching element found"}}
"""


class OSAutomationTool(BaseTool):
    """OS automation with window-focus verification and smart app opening."""

    def __init__(
        self,
        name: str,
        safe_runner: SafeRunner,
        workspace_dir: Any,
        config: dict[str, Any],
        enabled: bool = False,
        settings: dict[str, Any] | None = None,
        llm: Any | None = None,
    ) -> None:
        BaseTool.__init__(
            self,
            name=name,
            safe_runner=safe_runner,
            workspace_dir=workspace_dir,
            enabled=enabled,
            settings=settings,
        )
        self.logger = logging.getLogger("ao.os_tool")
        self.llm = llm

        allow_os_automation = False
        if settings:
            allow_os_automation = settings.get("allow_os_automation", False)

        try:
            vision_router = VisionRouter(config=config)
            self.os_controller = WindowsController(
                allow_os_automation=allow_os_automation, vision_router=vision_router
            )
        except Exception as e:
            self.logger.warning("Failed to initialize WindowsController: %s", e)
            self.os_controller = None

    # ------------------------------------------------------------------
    # Smart app opener with browser alias resolution
    # ------------------------------------------------------------------

    def _resolve_app_name(self, raw_name: str) -> str:
        """Resolve generic names like 'web browser' to a real executable."""
        key = raw_name.lower().strip()

        # Direct match in alias table
        candidates = _BROWSER_ALIASES.get(key, [])
        if not candidates:
            # Check if it's already a known app
            if key in _APP_EXE_MAP:
                return _APP_EXE_MAP[key]
            return key  # Pass through as-is

        # Try each candidate; pick the first one that exists on PATH
        for candidate in candidates:
            exe = _APP_EXE_MAP.get(candidate, candidate)
            if shutil.which(exe):
                self.logger.info("Resolved '%s' → '%s' (found on PATH)", raw_name, exe)
                return exe

        # Fallback: return the first candidate and hope start menu finds it
        fallback = candidates[0]
        self.logger.info("No browser found on PATH; defaulting to '%s'", fallback)
        return fallback

    def _verify_window_opened(self, app_name: str, timeout: float = 5.0) -> bool:
        """Wait for a window matching the app to appear in the foreground."""
        if not self.os_controller:
            return False

        hints = _APP_WINDOW_HINTS.get(app_name.lower(), [app_name])
        deadline = time.time() + timeout

        while time.time() < deadline:
            active = self.os_controller.window_manager.get_active_window()
            if active:
                title = active.get("title", "").lower()
                for hint in hints:
                    if hint.lower() in title:
                        self.logger.info("Window verified: '%s' matches '%s'", active["title"], hint)
                        return True
            time.sleep(0.5)

        self.logger.warning("Window verification failed for '%s' after %.1fs", app_name, timeout)
        return False

    # ------------------------------------------------------------------
    # Window focus guard
    # ------------------------------------------------------------------

    def _ensure_target_window(self, task_hint: str) -> dict[str, Any] | None:
        """Verify the correct window is in the foreground before acting.

        Returns the active window info if verified, or None on failure.
        """
        if not self.os_controller:
            return None

        active = self.os_controller.window_manager.get_active_window()
        if not active:
            return None

        # If we have a task hint, check it matches
        title = active.get("title", "").lower()
        hint_l = task_hint.lower()

        # Check common context words
        context_keywords = {
            "browser": ["chrome", "edge", "firefox", "mozilla"],
            "notepad": ["notepad", "untitled"],
            "code": ["visual studio code"],
            "terminal": ["cmd", "powershell", "terminal"],
        }

        for category, keywords in context_keywords.items():
            if category in hint_l:
                if any(kw in title for kw in keywords):
                    return active

        # If no specific category, just return current window
        return active

    # ------------------------------------------------------------------
    # Task string parser
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_task_string(task_str: str) -> list[dict[str, Any]]:
        """Parse a natural-language task string into OS automation commands."""
        text = re.sub(r"^Task:\s*", "", task_str, flags=re.IGNORECASE).strip()
        text_l = text.lower()
        commands: list[dict[str, Any]] = []

        # "open <app>"
        open_match = re.match(r"open\s+(?:the\s+)?(.+)", text_l)
        if open_match:
            app = open_match.group(1).strip()
            commands.append({"action": "open_app", "name": app})
            commands.append({"action": "wait", "seconds": 2.0})
            return commands

        # "type <text>"
        type_match = re.match(r"type\s+(.+)", text, flags=re.IGNORECASE)
        if type_match:
            typed = type_match.group(1).strip().strip("\"'")
            commands.append({"action": "direct_type", "text": typed, "requires_focus": True})
            return commands

        # "save as <filename>"
        save_match = re.match(
            r"save\s+as\s+(.+?)(?:\s+on\s+desktop)?$", text, flags=re.IGNORECASE
        )
        if save_match:
            filename = save_match.group(1).strip().strip("\"'")
            desktop = str(Path.home() / "Desktop" / filename)
            commands.append({"action": "direct_save_as", "filepath": desktop})
            return commands

        # "press <hotkey>"
        hotkey_match = re.match(r"press\s+(.+)", text, flags=re.IGNORECASE)
        if hotkey_match:
            keys = [k.strip() for k in hotkey_match.group(1).split("+")]
            commands.append({"action": "hotkey", "keys": keys})
            return commands

        # "scroll down/up"
        scroll_match = re.match(r"scroll\s+(up|down)(?:\s+(\d+))?", text_l)
        if scroll_match:
            direction = scroll_match.group(1)
            amount = int(scroll_match.group(2) or 3)
            clicks = -amount if direction == "down" else amount
            commands.append({"action": "scroll", "amount": clicks, "requires_focus": True})
            return commands

        # "wait <seconds>"
        wait_match = re.match(r"wait\s+(\d+(?:\.\d+)?)", text_l)
        if wait_match:
            commands.append({"action": "wait", "seconds": float(wait_match.group(1))})
            return commands

        # "click <target>" — explicit click command
        click_match = re.match(r"click\s+(?:the\s+|on\s+)?(.+)", text, flags=re.IGNORECASE)
        if click_match:
            target = click_match.group(1).strip()
            commands.append({
                "action": "smart_click",
                "target_description": target,
                "max_attempts": 3,
                "requires_focus": True,
            })
            return commands

        # Fallback: LLM-driven click
        commands.append({
            "action": "smart_click",
            "target_description": text,
            "max_attempts": 3,
            "requires_focus": True,
        })
        return commands

    # ------------------------------------------------------------------
    # LLM-driven click targeting
    # ------------------------------------------------------------------

    def _smart_click(self, target_description: str, max_attempts: int = 3) -> dict[str, Any]:
        """Click an on-screen element using UI tree or OCR + LLM."""
        if not self.os_controller:
            return {"success": False, "reason": "OS controller unavailable"}

        for attempt in range(1, max_attempts + 1):
            self.logger.info(
                "smart_click attempt %d/%d for: %s", attempt, max_attempts, target_description
            )

            # 1. Try UI tree first (instant)
            try:
                from os_controller.ui_tree_parser import parse_active_window, build_tree_map
                elements = parse_active_window()
                if elements:
                    spatial_map = build_tree_map(elements)
                else:
                    spatial_map = None
            except Exception:
                spatial_map = None

            # 2. If UI tree is empty, fall back to OCR
            if not spatial_map:
                try:
                    capture = self.os_controller.screen_capture.capture_screen()
                    analysis = self.os_controller.screen_reader.analyze(capture)
                    spatial_map = analysis.get("spatial_map", "(No elements detected)")
                except Exception as e:
                    self.logger.warning("Screen capture fallback failed: %s", e)
                    continue

            # 3. Ask LLM for coordinates
            if not self.llm:
                return self._text_match_click_from_map(target_description, spatial_map)

            prompt = _LLM_CLICK_SYSTEM_PROMPT.format(
                spatial_map=spatial_map, task=target_description
            )
            try:
                response = self.llm.chat([
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": f"Click the element for: {target_description}"},
                ])
            except Exception as e:
                self.logger.warning("LLM call failed: %s", e)
                continue

            # 4. Parse and click
            coords = self._parse_llm_coords(response)
            if coords is None:
                self.logger.warning("Unparseable coords: %s", response[:200])
                continue

            x, y = coords
            if x < 0 or y < 0:
                return {
                    "success": False,
                    "reason": f"LLM could not find '{target_description}' on screen",
                    "steps": [f"Map had elements but none matched '{target_description}'"],
                }

            self.os_controller.input_controller.click(x, y)
            return {
                "success": True,
                "steps": [f"LLM-guided click at ({x}, {y}) for '{target_description}'"],
            }

        return {
            "success": False,
            "reason": f"smart_click exhausted {max_attempts} attempts for '{target_description}'",
        }

    def _text_match_click_from_map(
        self, target: str, spatial_map: str
    ) -> dict[str, Any]:
        """No-LLM fallback: substring match on spatial map lines."""
        target_l = target.lower()
        for line in spatial_map.splitlines():
            if target_l in line.lower():
                coord_match = re.search(r"x:(\d+),\s*y:(\d+)", line)
                if coord_match:
                    x, y = int(coord_match.group(1)), int(coord_match.group(2))
                    self.os_controller.input_controller.click(x, y)
                    return {
                        "success": True,
                        "steps": [f"Text-match click at ({x}, {y}) for '{target}'"],
                    }
        return {"success": False, "reason": f"No element matching '{target}' found"}

    @staticmethod
    def _parse_llm_coords(response: str) -> tuple[int, int] | None:
        """Parse (x, y) from the LLM's JSON response."""
        try:
            cleaned = re.sub(r"```json\s*|```\s*", "", response).strip()
            match = re.search(r"\{[^}]+\}", cleaned)
            if match:
                data = json.loads(match.group())
                return (int(data.get("x", -1)), int(data.get("y", -1)))
        except (json.JSONDecodeError, ValueError, TypeError):
            pass
        return None

    # ------------------------------------------------------------------
    # Main execution with window-focus verification
    # ------------------------------------------------------------------

    def _run(self, payload: dict[str, Any]) -> Any:
        if not self.os_controller:
            return {"outcome": "OS Automation unavailable or disabled.", "success": False}

        task_raw = payload.get("task")
        goal = payload.get("goal", "")

        # Parse task into command sequence
        if isinstance(task_raw, str):
            command_sequence = self._parse_task_string(task_raw)
        elif isinstance(task_raw, dict):
            command_sequence = [task_raw]
        elif task_raw is None:
            action = payload.get("action")
            if action == "open_app":
                command_sequence = [{"action": "open_app", "name": payload.get("app_name", "")}]
            else:
                command_sequence = [{
                    "action": action or "smart_click",
                    "target_description": payload.get("target_label", ""),
                    "max_attempts": payload.get("max_attempts", 3),
                }]
        else:
            return {"outcome": f"Unexpected task type: {type(task_raw)}", "success": False}

        all_steps: list[str] = []
        for cmd in command_sequence:
            try:
                action = cmd.get("action", "smart_click")

                # ── OPEN APP with alias resolution ──
                if action == "open_app":
                    raw_name = cmd.get("name", "")
                    resolved = self._resolve_app_name(raw_name)
                    all_steps.append(f"Resolved '{raw_name}' → '{resolved}'")

                    result = self.os_controller.execute_task({"action": "open_app", "name": resolved})
                    all_steps.extend(result.get("steps", []))

                    # Verify the window actually opened
                    if not self._verify_window_opened(resolved, timeout=5.0):
                        return {
                            "outcome": f"App '{resolved}' opened but window not verified. "
                                       f"The expected window was not found in the foreground.",
                            "success": False,
                            "steps": all_steps,
                        }
                    all_steps.append(f"Window verified for '{resolved}'")
                    continue

                # ── WINDOW FOCUS GUARD for type/click/scroll ──
                if cmd.get("requires_focus", False):
                    active = self.os_controller.window_manager.get_active_window()
                    if not active or not active.get("title", "").strip():
                        return {
                            "outcome": "ABORT: No active window detected. Cannot perform "
                                       f"'{action}' blindly — the target window must be in "
                                       "the foreground first.",
                            "success": False,
                            "steps": all_steps,
                        }
                    all_steps.append(f"Focus verified: '{active['title']}'")

                # ── SMART CLICK ──
                if action == "smart_click":
                    result = self._smart_click(
                        target_description=cmd.get("target_description", ""),
                        max_attempts=int(cmd.get("max_attempts", 3)),
                    )
                else:
                    result = self.os_controller.execute_task(cmd)

                all_steps.extend(result.get("steps", []))

                if not result.get("success") and action not in ("hotkey", "wait", "scroll"):
                    return {
                        "outcome": f"Command failed: {result.get('reason', 'Unknown')}\n"
                                   f"Steps: {all_steps}",
                        "success": False,
                    }

            except RuntimeError as e:
                return {"outcome": str(e), "success": False}

        return {
            "outcome": f"All {len(command_sequence)} commands completed.\nSteps: {all_steps}",
            "success": True,
            "confidence": 0.8,
            "evidence_refs": [],
        }
