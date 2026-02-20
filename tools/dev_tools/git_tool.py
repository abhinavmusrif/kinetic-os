"""Workspace-limited git tool."""

from __future__ import annotations

import shlex
import subprocess
from typing import Any

from tools.base_tool import BaseTool


class GitTool(BaseTool):
    """Runs a constrained set of safe git commands."""

    SAFE_SUBCOMMANDS = {"status", "log", "branch", "diff", "rev-parse"}

    def _run(self, payload: dict[str, Any]) -> Any:
        command = str(payload.get("command", "git status")).strip()
        args = shlex.split(command)
        if not args or args[0] != "git":
            return {"outcome": "Only git commands are supported.", "confidence": 0.2}
        if len(args) < 2 or args[1] not in self.SAFE_SUBCOMMANDS:
            return {
                "outcome": f"Blocked git subcommand: {' '.join(args[1:])}",
                "confidence": 0.2,
            }
        proc = subprocess.run(
            args,
            cwd=self.workspace_dir,
            capture_output=True,
            text=True,
        )
        output = (proc.stdout or proc.stderr).strip()
        return {
            "outcome": output[:1500],
            "return_code": proc.returncode,
            "confidence": 0.8 if proc.returncode == 0 else 0.4,
        }
