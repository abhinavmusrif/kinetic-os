"""World state snapshot utilities."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


def workspace_tree_hash(workspace_dir: Path) -> str:
    """Compute stable hash over workspace file names and contents."""
    digest = hashlib.sha256()
    if not workspace_dir.exists():
        return digest.hexdigest()
    for file_path in sorted(p for p in workspace_dir.rglob("*") if p.is_file()):
        rel = file_path.relative_to(workspace_dir).as_posix()
        digest.update(rel.encode("utf-8"))
        digest.update(file_path.read_bytes())
    return digest.hexdigest()


def snapshot_world_state(
    workspace_dir: Path,
    open_windows: list[str] | None = None,
    last_actions: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build minimal world state snapshot."""
    return {
        "open_apps_windows": open_windows or [],
        "workspace_tree_hash": workspace_tree_hash(workspace_dir),
        "last_actions": last_actions or [],
    }
