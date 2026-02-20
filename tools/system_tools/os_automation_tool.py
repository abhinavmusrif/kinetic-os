"""OS Automation capability exposed as a tool to the planner."""

from __future__ import annotations

import logging
from typing import Any

from executor.safe_runner import SafeRunner
from os_controller.windows_controller import WindowsController
from tools.base_tool import BaseTool
from vision.vision_router import VisionRouter


class OSAutomationTool(BaseTool):
    """Tool for visually interacting with the host operating system."""

    def __init__(
        self,
        name: str,
        safe_runner: SafeRunner,
        workspace_dir: Any,
        config: dict[str, Any],
        enabled: bool = False,
        settings: dict[str, Any] | None = None,
    ) -> None:
        BaseTool.__init__(self, name=name, safe_runner=safe_runner, workspace_dir=workspace_dir, enabled=enabled, settings=settings)
        self.logger = logging.getLogger("ao.os_tool")
        
        allow_os_automation = False
        if settings:
            allow_os_automation = settings.get("allow_os_automation", False)
            
        try:
            vision_router = VisionRouter(config=config)
            self.os_controller = WindowsController(allow_os_automation=allow_os_automation, vision_router=vision_router)
        except Exception as e:
            self.logger.warning("Failed to initialize WindowsController: %s", e)
            self.os_controller = None

    def _run(self, payload: dict[str, Any]) -> Any:
        if not self.os_controller:
            return {"outcome": "OS Automation unavailable or disabled.", "success": False}
            
        action = payload.get("action", "click")
        app_name = payload.get("app_name", "")
        target_label = payload.get("target_label", "")
        text_to_type = payload.get("text_to_type", "")
        goal = payload.get("goal_description", "Unknown goal")

        if action == "open_app":
            if app_name:
                try:
                    outcome = self.os_controller.open_app(app_name)
                    return {"outcome": outcome, "success": True}
                except RuntimeError as e:
                    return {"outcome": str(e), "success": False}
            return {"outcome": "No app_name provided for open_app action.", "success": False}

        if target_label:
            try:
                success = self.os_controller.execute_visual_action(
                    goal_description=goal,
                    target_label=target_label,
                    action=action,
                    text_to_type=text_to_type
                )
                return {"outcome": f"Visual action '{action}' on '{target_label}' completed: {success}", "success": success}
            except RuntimeError as e:
                return {"outcome": str(e), "success": False}

        return {"outcome": "Invalid OS Automation payload. Require 'target_label' or 'app_name'.", "success": False}
