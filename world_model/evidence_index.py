"""Evidence indexing utilities for provenance tracking."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from memory.provenance import evidence_ref, sha256_file, sha256_text


class EvidenceIndex:
    """Indexes evidence references into memory store."""

    def __init__(self, memory_manager: Any) -> None:
        self.memory_manager = memory_manager

    def index_text(self, source_path: str, text: str) -> dict[str, Any]:
        content_hash = sha256_text(text)
        ref = evidence_ref("text", source_path, content_hash)
        return self.memory_manager.add_evidence(
            ref_id=ref,
            source_type="text",
            source_path=source_path,
            content_hash=content_hash,
        )

    def index_file(self, path: Path) -> dict[str, Any]:
        content_hash = sha256_file(path)
        ref = evidence_ref("file", str(path), content_hash)
        return self.memory_manager.add_evidence(
            ref_id=ref,
            source_type="file",
            source_path=str(path),
            content_hash=content_hash,
        )
