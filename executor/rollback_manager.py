"""Workspace checkpoint and rollback manager."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class RollbackManager:
    """Creates and restores workspace-local checkpoints."""

    def __init__(self, workspace_dir: Path) -> None:
        self.workspace_dir = workspace_dir.resolve()
        self.checkpoint_root = self.workspace_dir / ".checkpoints"
        self.checkpoint_root.mkdir(parents=True, exist_ok=True)

    def create_checkpoint(self, paths: list[Path] | None = None) -> str:
        """Capture copies of selected files under workspace."""
        checkpoint_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
        checkpoint_dir = self.checkpoint_root / checkpoint_id
        checkpoint_dir.mkdir(parents=True, exist_ok=True)

        if paths is None:
            source_paths = []
        else:
            source_paths = [p.resolve() for p in paths if p.exists() and p.is_file()]

        manifest: dict[str, Any] = {"files": []}
        for source in source_paths:
            if source.is_symlink():
                continue
            try:
                rel = source.relative_to(self.workspace_dir)
            except ValueError:
                continue
            target = checkpoint_dir / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(source.read_bytes())
            manifest["files"].append({"path": rel.as_posix()})

        (checkpoint_dir / "manifest.json").write_text(
            json.dumps(manifest, indent=2),
            encoding="utf-8",
        )
        return checkpoint_id

    def rollback(self, checkpoint_id: str) -> dict[str, Any]:
        """Restore files from a checkpoint."""
        checkpoint_dir = self.checkpoint_root / checkpoint_id
        manifest_path = checkpoint_dir / "manifest.json"
        if not manifest_path.exists():
            return {"success": False, "reason": f"Checkpoint not found: {checkpoint_id}"}

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        restored = 0
        for item in manifest.get("files", []):
            rel = Path(item["path"])
            source = checkpoint_dir / rel
            try:
                dest = (self.workspace_dir / rel).resolve()
                dest.relative_to(self.workspace_dir)
            except ValueError:
                continue

            if source.exists() and not source.is_symlink():
                dest.parent.mkdir(parents=True, exist_ok=True)
                if dest.exists() and dest.is_symlink():
                    dest.unlink()
                dest.write_bytes(source.read_bytes())
                restored += 1
        return {"success": True, "restored_files": restored, "checkpoint_id": checkpoint_id}
