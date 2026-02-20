"""Provenance and evidence hashing utilities."""

from __future__ import annotations

import hashlib
from pathlib import Path


def sha256_text(text: str) -> str:
    """Return SHA-256 hex digest for text."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    """Return SHA-256 hex digest for file contents."""
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def evidence_ref(source_type: str, source_path: str, content_hash: str) -> str:
    """Build stable evidence reference id."""
    raw = f"{source_type}:{source_path}:{content_hash}"
    return sha256_text(raw)[:24]
