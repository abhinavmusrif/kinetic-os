"""Blob store for binary artifacts."""

from __future__ import annotations

from pathlib import Path


class BlobStore:
    """Stores blobs inside workspace-local directory."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def put(self, name: str, data: bytes) -> Path:
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path
