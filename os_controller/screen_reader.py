"""Screen reading utility that combines capture + vision analysis."""

from __future__ import annotations

import json
import logging
import re
import tempfile
from pathlib import Path
from typing import TypedDict

from os_controller.screen_capture import CaptureResult
from vision.ocr.ocr_engine import OCREngine
from vision.vision_router import VisionRouter


class UIElement(TypedDict):
    """A detected user interface element."""
    role: str
    label: str
    bbox: list[int]
    confidence: float


class ScreenAnalysisResult(TypedDict):
    """Structured result of screen analysis."""
    elements: list[UIElement]
    state_summary: str
    warnings: list[str]


class ScreenReader:
    """Analyze screen content via VLM or OCR."""

    def __init__(self, vision_router: VisionRouter | None = None) -> None:
        self.logger = logging.getLogger("ao.screen_reader")
        self.vision_router = vision_router
        self.ocr_engine = OCREngine()

    def _should_use_vlm(self) -> bool:
        if not self.vision_router:
            return False
        # pylint: disable=protected-access
        return (
            self.vision_router.vlm_enabled
            and self.vision_router._gpu_available()
            and self.vision_router.vlm_provider.is_available()
        )

    def analyze(self, capture: CaptureResult, prompt: str | None = None) -> ScreenAnalysisResult:
        """Analyze a screen capture frame and return structured elements."""
        result: ScreenAnalysisResult = {
            "elements": [],
            "state_summary": "",
            "warnings": [],
        }

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp_path = Path(tmp.name)
        
        try:
            capture["image"].save(tmp_path)

            if self._should_use_vlm() and self.vision_router:
                # Attempt VLM structured analysis
                sys_prompt = prompt or (
                    "Analyze this screen image. Return ONLY a JSON object with keys: "
                    "'elements' (list of {role: string, label: string, bbox: [x1,y1,x2,y2], confidence: float}), "
                    "'state_summary' (string describing the screen), "
                    "and 'warnings' (list of strings). "
                    "Do not hallucinate elements or text."
                )
                try:
                    vlm_text = self.vision_router.vlm_provider.analyze(image_path=tmp_path, prompt=sys_prompt)
                    match = re.search(r"\{.*\}", vlm_text, re.DOTALL)
                    if match:
                        parsed = json.loads(match.group())
                        result["elements"] = parsed.get("elements", [])
                        result["state_summary"] = parsed.get("state_summary", "VLM analysis completed.")
                        result["warnings"] = parsed.get("warnings", [])
                        return result
                except Exception as e:
                    self.logger.warning("VLM JSON parsing failed: %s. Falling back to OCR.", e)
                    result["warnings"].append(f"VLM failed: {e}")

            # Fallback to pure OCR
            ocr_res = self.ocr_engine.extract(image_path=tmp_path)
            
            # If OCR returned empty text (e.g. Pillow fallback)
            if not ocr_res["text"] and ocr_res["confidence"] < 0.1:
                result["state_summary"] = "OCR fallback returned no text."
                result["warnings"].append(f"Metadata available: {ocr_res.get('metadata', {})}")
                return result
                
            elements: list[UIElement] = []
            for box in ocr_res.get("boxes", []):
                label = box.get("text", "")
                if not label:
                    continue
                left = box["left"]
                top = box["top"]
                right = left + box["width"]
                bottom = top + box["height"]
                elements.append({
                    "role": "text",
                    "label": label,
                    "bbox": [left, top, right, bottom],
                    "confidence": box.get("confidence", 0.0),
                })
                
            result["elements"] = elements
            result["state_summary"] = f"Extracted {len(elements)} text elements via OCR."
            return result

        finally:
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)
