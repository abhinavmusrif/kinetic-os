"""Workspace sandbox guards."""

from __future__ import annotations

from pathlib import Path


def is_within_workspace(path: Path, workspace_dir: Path) -> bool:
    """Return True if path is inside workspace directory."""
    try:
        path.resolve().relative_to(workspace_dir.resolve())
        return True
    except ValueError:
        return False
