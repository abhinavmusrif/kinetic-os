"""Screen reading utility — UI Tree first, OCR/VLM fallback.

Perception priority:
1. Native UI Automation tree (instant, highly accurate) via ui_tree_parser
2. VLM (Groq Vision) — if enabled and tree is empty
3. OCR (Tesseract) — always-available fallback
"""

from __future__ import annotations

import json
import logging
import re
import tempfile
from pathlib import Path
from typing import Any, TypedDict

from os_controller.screen_capture import CaptureResult
from vision.ocr.ocr_engine import OCRBox, OCREngine, OCRResult
from vision.vision_router import VisionRouter


class UIElement(TypedDict):
    """A detected user interface element."""

    role: str
    label: str
    bbox: list[int]
    center_x: int
    center_y: int
    confidence: float


class ScreenAnalysisResult(TypedDict):
    """Structured result of screen analysis."""

    elements: list[UIElement]
    spatial_map: str
    state_summary: str
    warnings: list[str]


# ---------------------------------------------------------------------------
# Spatial UI Map builder
# ---------------------------------------------------------------------------

def build_spatial_map(elements: list[UIElement]) -> str:
    """Build a compressed, numbered spatial map string for LLM consumption.

    Format:
        [ID: 0] "Login" @ (x:300, y:500)
        [ID: 1] "Submit" @ (x:300, y:550)
    """
    if not elements:
        return "(No UI elements detected on screen)"

    lines: list[str] = []
    for idx, elem in enumerate(elements):
        label = elem.get("label", "(unknown)")
        cx = elem.get("center_x", 0)
        cy = elem.get("center_y", 0)
        conf = elem.get("confidence", 0.0)
        role = elem.get("role", "")

        role_prefix = f"{role} " if role else ""
        lines.append(
            f'[ID: {idx}] {role_prefix}"{label}" @ (x:{cx}, y:{cy}) conf={conf:.2f}'
        )
    return "\n".join(lines)


def build_spatial_map_from_ocr(ocr_result: OCRResult) -> tuple[list[UIElement], str]:
    """Convert raw OCR result into UIElements and a spatial map string."""
    elements: list[UIElement] = []
    for box in ocr_result.get("boxes", []):
        label = box.get("text", "").strip()
        if not label:
            continue

        left = box["left"]
        top = box["top"]
        right = left + box["width"]
        bottom = top + box["height"]
        cx = box.get("center_x", left + box["width"] // 2)
        cy = box.get("center_y", top + box["height"] // 2)

        elements.append({
            "role": "text",
            "label": label,
            "bbox": [left, top, right, bottom],
            "center_x": cx,
            "center_y": cy,
            "confidence": box.get("confidence", 0.0),
        })

    spatial_map = build_spatial_map(elements)
    return elements, spatial_map


class ScreenReader:
    """Analyze screen content — UI Automation tree first, OCR/VLM fallback."""

    def __init__(self, vision_router: VisionRouter | None = None) -> None:
        self.logger = logging.getLogger("ao.screen_reader")
        self.vision_router = vision_router
        self.ocr_engine = OCREngine()

    def _should_use_vlm(self) -> bool:
        if not self.vision_router:
            return False
        if not self.vision_router.vlm_enabled:
            return False
        if self.vision_router.vlm_provider is None:
            return False
        return self.vision_router.vlm_provider.is_available()

    # ------------------------------------------------------------------
    # Primary: Native UI Automation tree (instant)
    # ------------------------------------------------------------------

    def _extract_ui_tree(self) -> tuple[list[UIElement], str]:
        """Extract elements via the native UIAutomation tree parser.

        This is the PRIMARY perception engine — instant and highly accurate.
        Returns (elements, spatial_map_string).
        """
        try:
            from os_controller.ui_tree_parser import (
                parse_active_window,
                build_tree_map,
            )

            tree_elements = parse_active_window()
            if not tree_elements:
                return [], ""

            # Convert tree elements to UIElement format
            ui_elements: list[UIElement] = []
            for el in tree_elements:
                ui_elements.append({
                    "role": el.element_type.lower(),
                    "label": el.label,
                    "bbox": [
                        el.center_x - el.width // 2,
                        el.center_y - el.height // 2,
                        el.center_x + el.width // 2,
                        el.center_y + el.height // 2,
                    ],
                    "center_x": el.center_x,
                    "center_y": el.center_y,
                    "confidence": 1.0,  # Native tree is 100% accurate
                })

            spatial_map = build_tree_map(tree_elements)
            self.logger.info("UI tree: extracted %d elements", len(ui_elements))
            return ui_elements, spatial_map

        except Exception as exc:
            self.logger.warning("UI tree extraction failed: %s", exc)
            return [], ""

    # ------------------------------------------------------------------
    # Full analysis pipeline
    # ------------------------------------------------------------------

    def analyze(self, capture: CaptureResult | None = None, prompt: str | None = None) -> ScreenAnalysisResult:
        """Analyze the current screen state.

        Priority:
        1. UI Automation tree (instant, primary)
        2. VLM (if tree is empty and VLM is available)
        3. OCR (always-available fallback)
        """
        result: ScreenAnalysisResult = {
            "elements": [],
            "spatial_map": "",
            "state_summary": "",
            "warnings": [],
        }

        # ── STEP 1: UI Automation tree (instant, primary) ──
        tree_elements, tree_map = self._extract_ui_tree()
        if tree_elements:
            result["elements"] = tree_elements
            result["spatial_map"] = tree_map
            result["state_summary"] = f"UI tree: {len(tree_elements)} interactable elements."
            return result

        # ── Tree was empty — need a screenshot for VLM/OCR ──
        if capture is None:
            result["state_summary"] = "UI tree empty and no screen capture provided."
            result["spatial_map"] = "(No UI elements detected)"
            result["warnings"].append("No capture available for VLM/OCR fallback")
            return result

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        try:
            capture["image"].save(tmp_path)

            # ── STEP 2: Try VLM ──
            if self._should_use_vlm() and self.vision_router:
                sys_prompt = prompt or (
                    "Analyze this screen image. Return ONLY a JSON object with keys: "
                    "'elements' (list of {role, label, bbox, center_x, center_y, confidence}), "
                    "'state_summary' (string), 'warnings' (list of strings)."
                )
                try:
                    vlm_text = self.vision_router.vlm_provider.analyze(
                        image_path=tmp_path, prompt=sys_prompt
                    )
                    match = re.search(r"\{.*\}", vlm_text, re.DOTALL)
                    if match:
                        parsed = json.loads(match.group())
                        result["elements"] = parsed.get("elements", [])
                        result["state_summary"] = parsed.get("state_summary", "VLM analysis.")
                        result["warnings"] = parsed.get("warnings", [])
                        result["spatial_map"] = build_spatial_map(result["elements"])
                        return result
                except Exception as e:
                    self.logger.warning("VLM failed: %s. Falling to OCR.", e)
                    result["warnings"].append(f"VLM failed: {e}")

            # ── STEP 3: OCR fallback ──
            ocr_res = self.ocr_engine.extract(image_path=tmp_path)

            if not ocr_res["text"] and ocr_res["confidence"] < 0.1:
                result["state_summary"] = "OCR returned no text."
                result["spatial_map"] = "(No UI elements detected on screen)"
                return result

            ocr_elements, spatial_map = build_spatial_map_from_ocr(ocr_res)
            result["elements"] = ocr_elements
            result["spatial_map"] = spatial_map
            result["state_summary"] = f"OCR: {len(ocr_elements)} text elements."
            return result

        finally:
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)

    def get_spatial_map(self, capture: CaptureResult | None = None) -> str:
        """Convenience method: return spatial map string only."""
        analysis = self.analyze(capture)
        return analysis.get("spatial_map", "(No elements detected)")
