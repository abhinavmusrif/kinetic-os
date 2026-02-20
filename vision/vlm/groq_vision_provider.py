"""Groq Vision-Language Model provider using llama-3.2-90b-vision-preview.

Sends a base64-encoded screenshot to Groq's OpenAI-compatible API and asks
the VLM to detect interactable UI elements (buttons, inputs, links) with
their label and approximate center (x, y) pixel coordinates.
"""

from __future__ import annotations

import base64
import logging
import os
from pathlib import Path
from typing import Any

from vision.base_vision import BaseVisionProvider

logger = logging.getLogger("ao.vision.groq_vlm")

_MODEL = "llama-3.2-90b-vision-preview"
_GROQ_BASE_URL = "https://api.groq.com/openai/v1"

_UI_DETECTOR_SYSTEM_PROMPT = """\
You are a UI element detector for an autonomous desktop operator.
Given a screenshot, identify ALL interactable elements visible in the image.

For each element, return:
- "label": the visible text or accessible name of the element
- "type": one of "button", "input", "link", "menu", "tab", "icon", "checkbox", "dropdown", "other"
- "x": approximate x pixel coordinate of the element's center
- "y": approximate y pixel coordinate of the element's center
- "confidence": your confidence (0.0 to 1.0) that this element exists at this location

Return ONLY a valid JSON array. No markdown, no explanation.

Example output:
[
  {"label": "Search", "type": "input", "x": 960, "y": 52, "confidence": 0.95},
  {"label": "Submit", "type": "button", "x": 1100, "y": 52, "confidence": 0.90},
  {"label": "Settings", "type": "menu", "x": 1880, "y": 15, "confidence": 0.85}
]

If no interactable elements are visible, return an empty array: []
"""


class GroqVisionProvider(BaseVisionProvider):
    """Real VLM provider using Groq's vision-capable LLM endpoint."""

    def __init__(self, model: str = _MODEL) -> None:
        self.model = model
        self._api_key: str | None = os.getenv("GROQ_API_KEY")

    def is_available(self) -> bool:
        """Check if the Groq API key is configured and openai package exists."""
        if not self._api_key:
            self._api_key = os.getenv("GROQ_API_KEY")
        if not self._api_key:
            return False
        try:
            import openai  # noqa: F401
            return True
        except ImportError:
            return False

    def analyze(self, image_path: Path, prompt: str | None = None) -> str:
        """Send a screenshot to Groq's VLM and return the analysis.

        Args:
            image_path: Path to the screenshot image file.
            prompt: Optional override prompt. If not provided, uses the
                    UI element detection system prompt.

        Returns:
            The VLM's text response (typically JSON array of UI elements).
        """
        if not self._api_key:
            self._api_key = os.getenv("GROQ_API_KEY")
        if not self._api_key:
            raise RuntimeError("GROQ_API_KEY not set — cannot use Groq VLM provider")

        # Read and encode the image
        image_path = Path(image_path)
        if not image_path.exists():
            raise FileNotFoundError(f"Screenshot not found: {image_path}")

        base64_image = self._encode_image(image_path)
        image_url = f"data:image/jpeg;base64,{base64_image}"

        # Build the prompt
        system_prompt = prompt or _UI_DETECTOR_SYSTEM_PROMPT

        # Build the multimodal message
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Analyze this screenshot and identify all interactable UI elements.",
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": image_url},
                    },
                ],
            },
        ]

        # Send to Groq
        try:
            from openai import OpenAI

            client = OpenAI(api_key=self._api_key, base_url=_GROQ_BASE_URL)
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.1,
                max_tokens=2048,
            )
            content = response.choices[0].message.content
            logger.info("Groq VLM response received (%d chars)", len(content or ""))
            return content or "[]"

        except Exception as exc:
            logger.error("Groq VLM API call failed: %s", exc)
            raise

    @staticmethod
    def _encode_image(image_path: Path) -> str:
        """Read an image file and return its base64-encoded string."""
        raw = image_path.read_bytes()
        return base64.b64encode(raw).decode("utf-8")
