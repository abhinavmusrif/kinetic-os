"""Tool registry and default tool wiring."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from executor.safe_runner import SafeRunner
from tools.base_tool import BaseTool
from tools.browser_tools.browser_controller import BrowserControllerTool
from tools.dev_tools.git_tool import GitTool
from tools.system_tools.file_tool import FileTool
from tools.system_tools.os_automation_tool import OSAutomationTool
from tools.system_tools.shell_tool import ShellTool


class MockTool(BaseTool):
    """Safe deterministic tool for offline end-to-end execution."""

    def _run(self, payload: dict[str, Any]) -> Any:
        task = str(payload.get("task", "mock task"))
        goal = str(payload.get("goal", ""))
        category = "general"
        task_l = task.lower()
        if "remember" in task_l or "preference" in task_l:
            category = "memory"
        elif "summarize" in task_l:
            category = "summarization"
        elif "verify" in task_l:
            category = "verification"
        return {
            "outcome": f"Executed deterministic task handler for '{task}' ({category}).",
            "goal": goal,
            "confidence": 0.9,
            "evidence_refs": [],
        }


@dataclass
class RegisteredTool:
    """Metadata for tool listing output."""

    name: str
    enabled: bool


class ToolRegistry:
    """Simple in-memory tool registry."""

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register(self, name: str, tool: BaseTool) -> None:
        self._tools[name] = tool

    def get(self, name: str) -> BaseTool | None:
        tool = self._tools.get(name)
        if tool and tool.enabled:
            return tool
        return None

    def list_tools(self) -> list[RegisteredTool]:
        return [
            RegisteredTool(name=name, enabled=tool.enabled)
            for name, tool in sorted(self._tools.items())
        ]


def _tool_enabled(config: dict[str, Any], tool_name: str, default: bool) -> bool:
    tools_cfg = config.get("tools", {})
    tool_cfg = tools_cfg.get(tool_name, {})
    if not isinstance(tool_cfg, dict):
        return default
    return bool(tool_cfg.get("enabled", default))


def _tool_settings(config: dict[str, Any], tool_name: str) -> dict[str, Any]:
    tools_cfg = config.get("tools", {})
    tool_cfg = tools_cfg.get(tool_name, {})
    if not isinstance(tool_cfg, dict):
        return {}
    return dict(tool_cfg)


def build_default_registry(
    *,
    root: Path,
    workspace_dir: Path,
    config: dict[str, Any],
    safe_runner: SafeRunner,
    llm: Any | None = None,
) -> ToolRegistry:
    """Build default tool registry from config."""
    _ = root
    registry = ToolRegistry()
    registry.register(
        "mock_tool",
        MockTool(
            name="mock_tool",
            safe_runner=safe_runner,
            workspace_dir=workspace_dir,
            enabled=_tool_enabled(config, "mock_tool", True),
            settings=_tool_settings(config, "mock_tool"),
        ),
    )
    registry.register(
        "file_tool",
        FileTool(
            name="file_tool",
            safe_runner=safe_runner,
            workspace_dir=workspace_dir,
            enabled=_tool_enabled(config, "file_tool", True),
            settings=_tool_settings(config, "file_tool"),
        ),
    )
    registry.register(
        "shell_tool",
        ShellTool(
            name="shell_tool",
            safe_runner=safe_runner,
            workspace_dir=workspace_dir,
            enabled=_tool_enabled(config, "shell_tool", False),
            settings=_tool_settings(config, "shell_tool"),
        ),
    )
    registry.register(
        "browser_tool",
        BrowserControllerTool(
            name="browser_tool",
            safe_runner=safe_runner,
            workspace_dir=workspace_dir,
            enabled=_tool_enabled(config, "browser_tool", False),
            settings=_tool_settings(config, "browser_tool"),
        ),
    )
    registry.register(
        "git_tool",
        GitTool(
            name="git_tool",
            safe_runner=safe_runner,
            workspace_dir=workspace_dir,
            enabled=_tool_enabled(config, "git_tool", False),
            settings=_tool_settings(config, "git_tool"),
        ),
    )
    registry.register(
        "os_automation_tool",
        OSAutomationTool(
            name="os_automation_tool",
            safe_runner=safe_runner,
            workspace_dir=workspace_dir,
            config=config,
            enabled=_tool_enabled(config, "os_automation_tool", True),
            settings=_tool_settings(config, "os_automation_tool"),
            llm=llm,
        ),
    )
    return registry
