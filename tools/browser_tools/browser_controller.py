"""Browser controller (disabled by default)."""

from __future__ import annotations

from tools.base_tool import BaseTool


class BrowserControllerTool(BaseTool):
    """Browser tool with safe deterministic behavior when enabled."""

    def metadata(self, payload: dict[str, object]) -> dict[str, object]:
        _ = payload
        return {"requires_network": True}

    def _run(self, payload: dict[str, object]) -> dict[str, object]:
        _ = payload
        return {
            "outcome": "Browser automation request recorded; no live browser session attached.",
            "confidence": 0.6,
        }
