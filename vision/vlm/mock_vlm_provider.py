"""Local fallback VLM provider using image metadata analysis."""

from __future__ import annotations

import statistics
from pathlib import Path

from vision.base_vision import BaseVisionProvider


class MockVLMProvider(BaseVisionProvider):
    """Always-available VLM fallback with deterministic image analysis."""

    def is_available(self) -> bool:
        return True

    def analyze(self, image_path: Path, prompt: str | None = None) -> str:
        prompt_part = f" Prompt: {prompt}" if prompt else ""
        if not image_path.exists():
            return f"[MOCK VLM] Image not found: {image_path}{prompt_part}"

        try:
            from PIL import Image

            image = Image.open(image_path).convert("L")
            width, height = image.size
            pixels = list(image.getdata())
            mean_luma = statistics.fmean(pixels) if pixels else 0.0
            dark_ratio = sum(1 for value in pixels if value < 64) / len(pixels) if pixels else 0.0
            return (
                f"[MOCK VLM] Image {image_path.name}: size={width}x{height}, "
                f"mean_luma={mean_luma:.1f}, dark_ratio={dark_ratio:.2f}.{prompt_part}"
            )
        except Exception:
            size = image_path.stat().st_size
            return f"[MOCK VLM] Image {image_path.name}: file_size_bytes={size}.{prompt_part}"
