"""Workspace-limited file tool."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from tools.base_tool import BaseTool


class FileTool(BaseTool):
    """Read/write/list files inside workspace only."""

    def _resolve_target(self, path_value: object | None) -> Path:
        if path_value is None:
            return self.workspace_dir.resolve()
        raw = Path(str(path_value))
        resolved = raw.resolve()
        try:
            resolved.relative_to(self.workspace_dir.resolve())
        except ValueError as exc:
            raise RuntimeError(f"Path traversal blocked: {resolved} is outside workspace.") from exc
        return resolved

    def metadata(self, payload: dict[str, Any]) -> dict[str, Any]:
        path = payload.get("path")
        if path is None:
            return {}
        return {"target_path": str(self._resolve_target(path))}

    def _run(self, payload: dict[str, Any]) -> Any:
        op = str(payload.get("op", "list")).lower()
        path_value = payload.get("path")
        target = self._resolve_target(path_value)

        if op == "list":
            base = self.workspace_dir if target == self.workspace_dir else target
            files = [p.name for p in base.iterdir()] if base.exists() else []
            return {"outcome": f"Listed {len(files)} entries.", "entries": files, "confidence": 0.9}

        if op == "read":
            text = target.read_text(encoding="utf-8")
            return {"outcome": text[:500], "confidence": 0.9}

        if op == "write":
            content = str(payload.get("content", ""))
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            return {"outcome": f"Wrote file {target}.", "confidence": 0.9}

        if op == "delete":
            if not bool(self.settings.get("allow_delete", False)):
                return {"outcome": "Delete operation disabled by tool settings.", "confidence": 1.0}
            if target.exists():
                target.unlink()
                return {"outcome": f"Deleted file {target}.", "confidence": 0.8}
            return {"outcome": f"File not found: {target}", "confidence": 0.7}

        return {"outcome": f"Unsupported file op: {op}", "confidence": 0.4}
