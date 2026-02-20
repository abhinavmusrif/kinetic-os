"""Tesseract OCR provider wrapper."""

from __future__ import annotations

from pathlib import Path

from vision.base_vision import BaseVisionProvider
from vision.ocr.ocr_engine import OCREngine


class TesseractProvider(BaseVisionProvider):
    """Uses `OCREngine` and exposes a text-only interface for vision routing."""

    def __init__(self) -> None:
        self.engine = OCREngine()

    def is_available(self) -> bool:
        return self.engine.has_tesseract()

    def analyze(self, image_path: Path, prompt: str | None = None) -> str:
        _ = prompt
        result = self.engine.extract(image_path=image_path)
        return result["text"]
