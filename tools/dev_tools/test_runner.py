"""Test runner tool."""

from __future__ import annotations

import subprocess
from typing import Any

from tools.base_tool import BaseTool


class TestRunnerTool(BaseTool):
    """Runs pytest inside workspace."""

    def _run(self, payload: dict[str, Any]) -> Any:
        _ = payload
        proc = subprocess.run(
            ["pytest", "-q"],
            cwd=self.workspace_dir,
            capture_output=True,
            text=True,
        )
        output = (proc.stdout or proc.stderr).strip()
        return {
            "outcome": output[:2000],
            "return_code": proc.returncode,
            "confidence": 0.8 if proc.returncode == 0 else 0.5,
        }
