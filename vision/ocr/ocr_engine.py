"""OCR engine with pytesseract provider and safe Pillow-based fallback."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, TypedDict


class OCRBox(TypedDict):
    """Bounding box for recognized text."""

    left: int
    top: int
    width: int
    height: int
    text: str
    confidence: float


class OCRResult(TypedDict):
    """Structured OCR result payload."""

    text: str
    confidence: float
    boxes: list[OCRBox]
    provider: str
    metadata: dict[str, Any]


class OCREngine:
    """Performs OCR with pytesseract when available, else Pillow metadata fallback."""

    def __init__(self) -> None:
        self.logger = logging.getLogger("ao.ocr")

    @staticmethod
    def _tesseract_available() -> bool:
        try:
            import pytesseract
            from PIL import Image  # noqa: F401

            _ = pytesseract.get_tesseract_version()
            return True
        except Exception:
            return False

    def has_tesseract(self) -> bool:
        """Return whether pytesseract+tesseract are available."""
        return self._tesseract_available()

    def extract(self, image_path: Path) -> OCRResult:
        """Extract text and boxes from image."""
        if not image_path.exists():
            return {
                "text": "",
                "confidence": 0.0,
                "boxes": [],
                "provider": "missing-file",
                "metadata": {},
            }
        if self._tesseract_available():
            return self._extract_with_tesseract(image_path=image_path)
        return self._extract_with_pillow_fallback(image_path=image_path)

    def _extract_with_tesseract(self, image_path: Path) -> OCRResult:
        try:
            import pytesseract
            from PIL import Image

            image = Image.open(image_path)
            data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
            texts: list[str] = []
            boxes: list[OCRBox] = []
            confidences: list[float] = []

            text_items = data.get("text", [])
            conf_items = data.get("conf", [])
            left_items = data.get("left", [])
            top_items = data.get("top", [])
            width_items = data.get("width", [])
            height_items = data.get("height", [])

            for idx, raw_text in enumerate(text_items):
                text = str(raw_text).strip()
                if not text:
                    continue
                try:
                    conf = float(conf_items[idx])
                except Exception:
                    conf = 0.0
                if conf < 0:
                    continue
                norm_conf = max(0.0, min(1.0, conf / 100.0))
                box: OCRBox = {
                    "left": int(left_items[idx]),
                    "top": int(top_items[idx]),
                    "width": int(width_items[idx]),
                    "height": int(height_items[idx]),
                    "text": text,
                    "confidence": norm_conf,
                }
                texts.append(text)
                confidences.append(norm_conf)
                boxes.append(box)
            joined = " ".join(texts).strip()
            average_conf = sum(confidences) / len(confidences) if confidences else 0.0
            return {
                "text": joined,
                "confidence": average_conf,
                "boxes": boxes,
                "provider": "tesseract",
                "metadata": {},
            }
        except Exception as exc:
            self.logger.warning("Tesseract OCR failed, using Pillow fallback: %s", exc)
            return self._extract_with_pillow_fallback(image_path=image_path)

    def _extract_with_pillow_fallback(self, image_path: Path) -> OCRResult:
        """Extract textual metadata using Pillow as a safe fallback."""
        try:
            from PIL import ExifTags, Image
        except Exception:
            return {
                "text": "",
                "confidence": 0.0,
                "boxes": [],
                "provider": "fallback-unavailable",
                "metadata": {},
            }

        metadata_dict: dict[str, Any] = {}
        try:
            image = Image.open(image_path)
            metadata_dict["format"] = getattr(image, "format", None)
            metadata_dict["size"] = getattr(image, "size", None)
            metadata_dict["mode"] = getattr(image, "mode", None)
            
            info_text = getattr(image, "text", {})
            if isinstance(info_text, dict):
                metadata_dict.update(info_text)

            exif = image.getexif()
            if exif:
                tags = {ExifTags.TAGS.get(k, str(k)): v for k, v in exif.items()}
                metadata_dict["exif"] = tags
        except Exception as exc:
            self.logger.warning("Pillow fallback failed: %s", exc)

        return {
            "text": "",
            "confidence": 0.05,
            "boxes": [],
            "provider": "pillow-fallback",
            "metadata": metadata_dict,
        }
