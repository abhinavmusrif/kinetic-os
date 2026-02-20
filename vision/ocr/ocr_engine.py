"""OCR engine with Tesseract provider, center-coordinate extraction, and Pillow fallback.

Returns structured ``OCRResult`` payloads containing per-word bounding boxes,
normalized confidence scores, and absolute center (x, y) coordinates for every
recognized text element — suitable for Spatial UI Mapping.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, TypedDict


class OCRBox(TypedDict):
    """Bounding box for recognized text with center coordinates."""

    left: int
    top: int
    width: int
    height: int
    center_x: int
    center_y: int
    text: str
    confidence: float


class OCRResult(TypedDict):
    """Structured OCR result payload."""

    text: str
    confidence: float
    boxes: list[OCRBox]
    provider: str
    metadata: dict[str, Any]


# Minimum normalized confidence (0-1) to keep a detected word.
_MIN_CONFIDENCE = 0.60


class OCREngine:
    """Performs OCR with pytesseract when available, else Pillow metadata fallback.

    The Tesseract path uses ``image_to_data(output_type=Output.DICT)`` so every
    recognized word comes back with its bounding box.  We filter out blanks and
    low-confidence artifacts, then compute the absolute center (x, y) for each
    valid block.
    """

    def __init__(self) -> None:
        self.logger = logging.getLogger("ao.ocr")

    # ------------------------------------------------------------------
    # Availability
    # ------------------------------------------------------------------

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
        """Return whether pytesseract + tesseract binary are available."""
        return self._tesseract_available()

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def extract(self, image_path: Path) -> OCRResult:
        """Extract text, boxes, and center coordinates from an image."""
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

    # ------------------------------------------------------------------
    # Tesseract extraction (with bounding boxes + centers)
    # ------------------------------------------------------------------

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
                word = str(raw_text).strip()
                if not word:
                    continue

                # Parse confidence (pytesseract returns -1 for non-text rows)
                try:
                    raw_conf = float(conf_items[idx])
                except Exception:
                    raw_conf = -1.0
                if raw_conf < 0:
                    continue

                norm_conf = max(0.0, min(1.0, raw_conf / 100.0))
                if norm_conf < _MIN_CONFIDENCE:
                    continue

                left = int(left_items[idx])
                top = int(top_items[idx])
                width = int(width_items[idx])
                height = int(height_items[idx])

                # Compute absolute center
                center_x = left + width // 2
                center_y = top + height // 2

                box: OCRBox = {
                    "left": left,
                    "top": top,
                    "width": width,
                    "height": height,
                    "center_x": center_x,
                    "center_y": center_y,
                    "text": word,
                    "confidence": norm_conf,
                }
                texts.append(word)
                confidences.append(norm_conf)
                boxes.append(box)

            joined = " ".join(texts).strip()
            avg_conf = sum(confidences) / len(confidences) if confidences else 0.0

            return {
                "text": joined,
                "confidence": avg_conf,
                "boxes": boxes,
                "provider": "tesseract",
                "metadata": {"word_count": len(boxes)},
            }
        except Exception as exc:
            self.logger.warning("Tesseract OCR failed, using Pillow fallback: %s", exc)
            return self._extract_with_pillow_fallback(image_path=image_path)

    # ------------------------------------------------------------------
    # Pillow fallback (metadata only, no bounding boxes)
    # ------------------------------------------------------------------

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
