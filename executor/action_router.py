"""Routes tasks to registered tools."""

from __future__ import annotations

from typing import Any


class ActionRouter:
    """Select tool based on task text and invoke it."""

    def __init__(self, tool_registry: Any) -> None:
        self.tool_registry = tool_registry

    def run(self, task: str, goal: str) -> dict[str, Any]:
        """Route task to best matching tool."""
        task_l = task.lower()
        if "file" in task_l:
            tool_name = "file_tool"
        elif "git" in task_l:
            tool_name = "git_tool"
        elif "shell" in task_l:
            tool_name = "shell_tool"
        else:
            tool_name = "mock_tool"
        tool = self.tool_registry.get(tool_name)
        if tool is None:
            return {
                "success": False,
                "action": task,
                "outcome": f"No tool registered: {tool_name}",
                "confidence": 0.2,
            }
        result = tool.execute({"task": task, "goal": goal})
        return {
            "success": bool(result.get("success", True)),
            "action": task,
            "outcome": result.get("outcome", "completed"),
            "confidence": float(result.get("confidence", 0.7)),
            "evidence_refs": list(result.get("evidence_refs", [])),
        }
