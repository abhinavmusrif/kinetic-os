"""Episode compression utilities."""

from __future__ import annotations


class Compressor:
    """Creates compact summaries for archival views."""

    @staticmethod
    def compress(summary: str) -> str:
        """Return a short compressed summary."""
        return summary[:120]
