"""Vision router selecting VLM or OCR fallback."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from vision.base_vision import BaseVisionProvider
from vision.ocr.ocr_engine import OCREngine
from vision.ocr.tesseract_provider import TesseractProvider
from vision.vlm.mock_vlm_provider import MockVLMProvider


class OCRProvider(BaseVisionProvider):
    """OCR provider that always returns best-effort extraction."""

    def __init__(self) -> None:
        self.engine = OCREngine()

    def is_available(self) -> bool:
        return True

    def analyze(self, image_path: Path, prompt: str | None = None) -> str:
        _ = prompt
        return self.engine.extract(image_path=image_path)["text"]


class VisionRouter:
    """Choose vision backend based on config and availability."""

    def __init__(self, config: dict[str, Any]) -> None:
        self.logger = logging.getLogger("ao.vision")
        models_cfg = config.get("models", {}).get("vision", {})
        runtime_cfg = config.get("runtime", {})
        self.vlm_enabled = bool(models_cfg.get("vlm_enabled", runtime_cfg.get("enable_vlm", False)))
        self.ocr_enabled = bool(models_cfg.get("ocr_enabled", runtime_cfg.get("enable_ocr", True)))

        self.vlm_provider: BaseVisionProvider = MockVLMProvider()
        self.ocr_provider: BaseVisionProvider = (
            TesseractProvider() if self.ocr_enabled else OCRProvider()
        )

    def analyze(self, image_path: Path, prompt: str | None = None) -> str:
        """Route request to VLM when enabled/available, otherwise OCR fallback."""
        if self.vlm_enabled and isinstance(self.vlm_provider, MockVLMProvider):
            self.logger.info("Using mock VLM provider (no GPU required).")
            return self.vlm_provider.analyze(image_path=image_path, prompt=prompt)

        if self.vlm_enabled and not self._gpu_available():
            self.logger.warning("VLM enabled but no GPU detected. Falling back to OCR.")

        if self.vlm_enabled and self._gpu_available() and self.vlm_provider.is_available():
            return self.vlm_provider.analyze(image_path=image_path, prompt=prompt)

        if self.vlm_enabled:
            self.logger.warning("VLM unavailable. Falling back to OCR.")
        if self.ocr_provider.is_available():
            return self.ocr_provider.analyze(image_path=image_path, prompt=prompt)
        self.logger.warning("OCR provider unavailable. Falling back to internal OCR engine.")
        return OCRProvider().analyze(image_path=image_path, prompt=prompt)

    @staticmethod
    def _gpu_available() -> bool:
        """Best-effort GPU detection."""
        try:
            import torch

            return bool(torch.cuda.is_available())
        except Exception:
            return False
