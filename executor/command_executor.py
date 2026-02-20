"""Command execution wrapper."""

from __future__ import annotations

import subprocess
from pathlib import Path


def run_command(command: list[str], cwd: Path | None = None) -> tuple[int, str, str]:
    """Run command and return (exit_code, stdout, stderr)."""
    proc = subprocess.run(command, cwd=cwd, capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr
