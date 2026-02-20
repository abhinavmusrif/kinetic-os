"""System inspection helpers for basic runtime diagnostics."""

from __future__ import annotations

import platform
import sys
from pathlib import Path


def inspect_system() -> dict[str, str]:
    """Return lightweight host information."""
    return {
        "platform": platform.platform(),
        "python_version": sys.version.split()[0],
        "cwd": str(Path.cwd()),
    }
