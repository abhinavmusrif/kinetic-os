"""Shell execution tool (disabled by default)."""

from __future__ import annotations

import subprocess
from typing import Any

from tools.base_tool import BaseTool


class ShellTool(BaseTool):
    """Runs shell commands when explicitly enabled by config and policy."""

    def _run(self, payload: dict[str, Any]) -> Any:
        command = payload.get("command") or payload.get("task")
        if not isinstance(command, str) or not command.strip():
            return {"outcome": "No command provided.", "confidence": 0.2}
        proc = subprocess.run(
            command,
            shell=True,
            cwd=self.workspace_dir,
            capture_output=True,
            text=True,
        )
        output = proc.stdout.strip() or proc.stderr.strip()
        return {
            "outcome": output[:1000],
            "return_code": proc.returncode,
            "confidence": 0.8 if proc.returncode == 0 else 0.4,
        }
