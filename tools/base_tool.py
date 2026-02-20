"""Base tool interface and execution wrapper."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from executor.safe_runner import SafeRunner


class BaseTool(ABC):
    """Base class for all tools with safe-runner integration."""

    def __init__(
        self,
        name: str,
        safe_runner: SafeRunner,
        workspace_dir: Path,
        enabled: bool = True,
        settings: dict[str, Any] | None = None,
    ) -> None:
        self.name = name
        self.safe_runner = safe_runner
        self.workspace_dir = workspace_dir
        self.enabled = enabled
        self.settings = settings or {}

    def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Execute tool with governance checks."""
        if not self.enabled:
            return {
                "success": False,
                "tool": self.name,
                "outcome": f"Tool '{self.name}' disabled.",
                "confidence": 1.0,
            }
        action = str(payload.get("task") or payload.get("action") or f"{self.name}:execute")
        metadata = self.metadata(payload)
        if self.settings.get("require_confirmation", False):
            metadata = {**metadata, "requires_confirmation": True}
        return self.safe_runner.run(
            action=action,
            tool_name=self.name,
            inputs=payload,
            metadata=metadata,
            execute=lambda: self._run(payload),
        )

    @abstractmethod
    def _run(self, payload: dict[str, Any]) -> Any:
        """Tool-specific execution logic."""

    def metadata(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Optional metadata used for policy checks."""
        _ = payload
        return {}
