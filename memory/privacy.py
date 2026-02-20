"""Privacy utilities for memory records."""

from __future__ import annotations

VALID_PRIVACY_LEVELS = {"public", "internal", "restricted"}


def normalize_privacy_level(level: str) -> str:
    """Normalize privacy levels to supported values."""
    level_norm = level.lower().strip()
    if level_norm in VALID_PRIVACY_LEVELS:
        return level_norm
    return "internal"
