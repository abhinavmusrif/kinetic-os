"""Vision router selecting VLM or OCR fallback.

When vlm_enabled is true in config AND the GROQ_API_KEY is set, uses the
real GroqVisionProvider (llama-3.2-90b-vision-preview). If the VLM call
fails or times out, falls back to OCR transparently.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from vision.base_vision import BaseVisionProvider
from vision.ocr.ocr_engine import OCREngine
from vision.ocr.tesseract_provider import TesseractProvider

logger = logging.getLogger("ao.vision")


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
    """Choose vision backend based on config and availability.

    Priority order:
    1. GroqVisionProvider (real VLM) — if vlm_enabled and GROQ_API_KEY set
    2. MockVLMProvider — if vlm_enabled but no API key (deterministic fallback)
    3. TesseractProvider / OCRProvider — always-available OCR fallback
    """

    def __init__(self, config: dict[str, Any]) -> None:
        models_cfg = config.get("models", {}).get("vision", {})
        runtime_cfg = config.get("runtime", {})
        self.vlm_enabled = bool(
            models_cfg.get("vlm_enabled", runtime_cfg.get("enable_vlm", False))
        )
        self.ocr_enabled = bool(
            models_cfg.get("ocr_enabled", runtime_cfg.get("enable_ocr", True))
        )

        # --- VLM provider selection ---
        self.vlm_provider: BaseVisionProvider | None = None
        if self.vlm_enabled:
            self.vlm_provider = self._build_vlm_provider()

        # --- OCR provider (always available as fallback) ---
        self.ocr_provider: BaseVisionProvider = (
            TesseractProvider() if self.ocr_enabled else OCRProvider()
        )

    @staticmethod
    def _build_vlm_provider() -> BaseVisionProvider:
        """Attempt to instantiate the real Groq VLM; fall back to Mock."""
        try:
            from vision.vlm.groq_vision_provider import GroqVisionProvider

            provider = GroqVisionProvider()
            if provider.is_available():
                logger.info(
                    "GroqVisionProvider active (model=%s)", provider.model
                )
                return provider
            logger.warning(
                "GroqVisionProvider not available (missing API key or openai). "
                "Falling back to MockVLMProvider."
            )
        except Exception as exc:
            logger.warning("Failed to load GroqVisionProvider: %s", exc)

        from vision.vlm.mock_vlm_provider import MockVLMProvider

        return MockVLMProvider()

    def analyze(self, image_path: Path, prompt: str | None = None) -> str:
        """Route request to VLM first, fall back to OCR on any failure."""
        # --- Try VLM first ---
        if self.vlm_enabled and self.vlm_provider is not None:
            try:
                result = self.vlm_provider.analyze(
                    image_path=image_path, prompt=prompt
                )
                logger.info("VLM analysis succeeded")
                return result
            except Exception as exc:
                logger.warning(
                    "VLM analysis failed — falling back to OCR: %s", exc
                )

        # --- OCR fallback ---
        if self.ocr_provider.is_available():
            return self.ocr_provider.analyze(image_path=image_path, prompt=prompt)

        logger.warning("OCR provider unavailable. Using internal OCR engine.")
        return OCRProvider().analyze(image_path=image_path, prompt=prompt)
