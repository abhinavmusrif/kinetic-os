"""Base vision provider abstractions."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class BaseVisionProvider(ABC):
    """Abstract interface for VLM/OCR providers."""

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if provider is available in current environment."""

    @abstractmethod
    def analyze(self, image_path: Path, prompt: str | None = None) -> str:
        """Analyze an image and return text output."""
