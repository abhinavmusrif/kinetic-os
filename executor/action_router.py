"""LLM-driven action routing with Spatial UI Map fallback for visual tasks.

When the Vision Router confirms VLM is disabled and the task requires clicking
a visual element, the router captures the screen, builds a Spatial UI Map via
OCR, and asks the text LLM to pick the (x, y) coordinate.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

_ROUTING_SYSTEM_PROMPT = """\
You are a tool selection engine for an autonomous desktop operator.
Given a task description and a list of available tools, select the BEST tool to execute the task.

Available tools:
{tool_list}

Rules:
- Respond with ONLY a JSON object, no markdown, no explanation.
- The JSON must have exactly two keys: "tool" and "reason".
- "tool" must be one of the tool names listed above.
- "reason" should be a brief explanation of why this tool was selected.
- If the task involves desktop apps, windows, typing, clicking, or opening programs, use "os_automation_tool".
- If the task involves reading, writing, or listing files in the workspace, use "file_tool".
- If the task involves running shell commands, use "shell_tool".
- If the task involves git operations, use "git_tool".
- If the task involves web browsing, use "browser_tool".
- If none clearly match, use "mock_tool" as a safe default.

Example:
Task: "open notepad and type hello"
Response: {{"tool": "os_automation_tool", "reason": "Task involves opening a desktop application and typing text"}}
"""

_SPATIAL_CLICK_PROMPT = """\
You are a screen interaction engine for an autonomous desktop operator.
Below is the parsed screen data — a numbered list of text elements detected on
the current screen, each with its (x, y) pixel coordinate.

{ui_map}

To achieve the current task: "{task}"
Which (x, y) coordinate should the mouse click?

Reply strictly with JSON containing x and y:
{{"x": <integer>, "y": <integer>, "reason": "<brief explanation>"}}

If no suitable element is found, reply with:
{{"x": -1, "y": -1, "reason": "No matching element found"}}
"""

logger = logging.getLogger("ao.action_router")


class ActionRouter:
    """LLM-driven tool selection and task execution with Spatial UI Map fallback."""

    def __init__(self, tool_registry: Any, llm: Any | None = None) -> None:
        self.tool_registry = tool_registry
        self.llm = llm

    def run(self, task: str, goal: str) -> dict[str, Any]:
        """Route task to best matching tool using LLM, with keyword fallback."""
        # --- Primary: LLM-based routing ---
        if self.llm is not None:
            try:
                tool_name = self._llm_select_tool(task)
                if tool_name:
                    result = self._execute_tool(tool_name, task, goal)
                    # If the tool failed and this looks like a visual click task,
                    # try the Spatial UI Map fallback
                    if not result.get("success") and self._is_visual_click_task(task):
                        logger.info("Tool failed on visual task; trying Spatial UI Map fallback")
                        spatial_result = self._spatial_ui_click(task)
                        if spatial_result.get("success"):
                            return spatial_result
                    return result
            except Exception as exc:
                logger.warning("LLM routing failed: %s — falling back to keywords", exc)

        # --- Fallback: keyword-based routing ---
        tool_name = self._keyword_select_tool(task)
        return self._execute_tool(tool_name, task, goal)

    # ------------------------------------------------------------------
    # LLM-based tool selection
    # ------------------------------------------------------------------

    def _llm_select_tool(self, task: str) -> str | None:
        """Ask the LLM which tool to use for a given task."""
        tool_list = self._build_tool_list()
        prompt = _ROUTING_SYSTEM_PROMPT.format(tool_list=tool_list)

        response = self.llm.chat(
            [
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"Task: {task}"},
            ]
        )

        return self._parse_tool_selection(response)

    def _build_tool_list(self) -> str:
        """Build a formatted list of available tools for the LLM prompt."""
        lines: list[str] = []
        for reg_tool in self.tool_registry.list_tools():
            status = "enabled" if reg_tool.enabled else "disabled"
            lines.append(f"- {reg_tool.name} ({status})")
        return "\n".join(lines)

    def _parse_tool_selection(self, response: str) -> str | None:
        """Parse the LLM response to extract the selected tool name."""
        try:
            cleaned = re.sub(r"```json\s*|```\s*", "", response).strip()
            data = json.loads(cleaned)
            tool_name = data.get("tool", "").strip()
            if tool_name and self.tool_registry.get(tool_name) is not None:
                reason = data.get("reason", "")
                logger.info("LLM selected tool '%s': %s", tool_name, reason)
                return tool_name
            elif tool_name:
                logger.warning("LLM selected unknown/disabled tool '%s'", tool_name)
                return None
        except (json.JSONDecodeError, AttributeError):
            pass

        # Fallback: scan response text for tool names
        response_lower = response.lower()
        for reg_tool in self.tool_registry.list_tools():
            if reg_tool.enabled and reg_tool.name in response_lower:
                logger.info("Extracted tool '%s' from LLM text response", reg_tool.name)
                return reg_tool.name

        return None

    # ------------------------------------------------------------------
    # Keyword fallback
    # ------------------------------------------------------------------

    @staticmethod
    def _keyword_select_tool(task: str) -> str:
        """Fallback keyword-based tool selection."""
        task_l = task.lower()
        if "file" in task_l and ("read" in task_l or "write" in task_l or "list" in task_l):
            return "file_tool"
        if "git" in task_l:
            return "git_tool"
        if "shell" in task_l or "command" in task_l or "terminal" in task_l:
            return "shell_tool"
        if any(kw in task_l for kw in [
            "open", "notepad", "window", "click", "type", "app",
            "desktop", "save", "close", "minimize", "maximize",
        ]):
            return "os_automation_tool"
        if any(kw in task_l for kw in ["browse", "browser", "url", "website", "web"]):
            return "browser_tool"
        return "mock_tool"

    # ------------------------------------------------------------------
    # Spatial UI Map fallback (OCR → LLM → click)
    # ------------------------------------------------------------------

    @staticmethod
    def _is_visual_click_task(task: str) -> bool:
        """Detect if a task requires clicking a visual element on screen."""
        visual_kw = ["click", "select", "press", "choose", "tap", "button", "menu", "link"]
        task_l = task.lower()
        return any(kw in task_l for kw in visual_kw)

    def _spatial_ui_click(self, task: str) -> dict[str, Any]:
        """Capture screen, build spatial UI map, ask LLM for click coords.

        Pipeline:
        1. Get the OS automation tool's controller for screen capture
        2. Capture the screen → run OCR → build spatial map
        3. Ask the text LLM: "Given this map, where should I click?"
        4. Parse JSON response → click at (x, y)
        """
        if not self.llm:
            return {"success": False, "action": task, "outcome": "No LLM for spatial click"}

        # Get the OS controller from the os_automation_tool
        os_tool = self.tool_registry.get("os_automation_tool")
        if os_tool is None or not hasattr(os_tool, "os_controller") or os_tool.os_controller is None:
            return {"success": False, "action": task, "outcome": "OS controller unavailable for spatial click"}

        ctl = os_tool.os_controller

        try:
            # 1. Capture the screen
            capture = ctl.screen_capture.capture_screen()

            # 2. Build the spatial UI map
            analysis = ctl.screen_reader.analyze(capture)
            ui_map = analysis.get("spatial_map", "(No elements detected)")

            if "(No" in ui_map:
                return {
                    "success": False,
                    "action": task,
                    "outcome": "Spatial map is empty — no OCR elements detected on screen",
                    "confidence": 0.2,
                    "evidence_refs": [],
                }

            # 3. Ask the LLM
            prompt = _SPATIAL_CLICK_PROMPT.format(ui_map=ui_map, task=task)
            response = self.llm.chat(
                [
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": f"Click for task: {task}"},
                ]
            )

            # 4. Parse coordinates
            coords = self._parse_coords(response)
            if coords is None:
                return {
                    "success": False,
                    "action": task,
                    "outcome": f"LLM returned unparseable coordinates: {response[:200]}",
                    "confidence": 0.2,
                    "evidence_refs": [],
                }

            x, y = coords
            if x < 0 or y < 0:
                return {
                    "success": False,
                    "action": task,
                    "outcome": "LLM could not find a matching element on screen",
                    "confidence": 0.3,
                    "evidence_refs": [],
                }

            # 5. Click!
            ctl.input_controller.click(x, y)
            logger.info("Spatial UI Map click at (%d, %d) for task: %s", x, y, task)
            return {
                "success": True,
                "action": task,
                "tool_used": "spatial_ui_map",
                "outcome": f"Clicked at ({x}, {y}) via Spatial UI Map for: {task}",
                "confidence": 0.75,
                "evidence_refs": [],
            }

        except Exception as exc:
            logger.warning("Spatial UI Map click failed: %s", exc)
            return {
                "success": False,
                "action": task,
                "outcome": f"Spatial click error: {exc}",
                "confidence": 0.1,
                "evidence_refs": [],
            }

    @staticmethod
    def _parse_coords(response: str) -> tuple[int, int] | None:
        """Parse (x, y) from the LLM's JSON response."""
        try:
            cleaned = re.sub(r"```json\s*|```\s*", "", response).strip()
            match = re.search(r"\{[^}]+\}", cleaned)
            if match:
                data = json.loads(match.group())
                x = int(data.get("x", -1))
                y = int(data.get("y", -1))
                return (x, y)
        except (json.JSONDecodeError, ValueError, TypeError):
            pass
        return None

    # ------------------------------------------------------------------
    # Tool execution
    # ------------------------------------------------------------------

    def _execute_tool(self, tool_name: str, task: str, goal: str) -> dict[str, Any]:
        """Execute the selected tool and return a standardized result."""
        tool = self.tool_registry.get(tool_name)
        if tool is None:
            logger.warning("Tool '%s' not found or disabled, falling back to mock_tool", tool_name)
            tool = self.tool_registry.get("mock_tool")
            if tool is None:
                return {
                    "success": False,
                    "action": task,
                    "outcome": f"No tool available: {tool_name}",
                    "confidence": 0.1,
                    "evidence_refs": [],
                }
        result = tool.execute({"task": task, "goal": goal})
        return {
            "success": bool(result.get("success", True)),
            "action": task,
            "tool_used": tool_name,
            "outcome": result.get("outcome", "completed"),
            "confidence": float(result.get("confidence", 0.7)),
            "evidence_refs": list(result.get("evidence_refs", [])),
        }
