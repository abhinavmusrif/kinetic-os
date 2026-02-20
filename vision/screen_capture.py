"""Cross-platform screen capture utility with safe stubs."""

from __future__ import annotations

from pathlib import Path


def capture_screen(output_path: Path) -> Path | None:
    """Capture screen using Pillow if available, otherwise return None."""
    try:
        from PIL import ImageGrab

        image = ImageGrab.grab()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        image.save(output_path)
        return output_path
    except Exception:
        return None
