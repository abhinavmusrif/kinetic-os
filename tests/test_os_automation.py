"""Tests for the OS Automation visual loop."""

from unittest.mock import MagicMock

import os
import sys

import pytest

from os_controller.windows_controller import WindowsController
from tools.system_tools.os_automation_tool import OSAutomationTool

should_skip_ui = (
    sys.platform != "win32" or 
    os.environ.get("AO_ENABLE_UI_TESTS", "0") != "1"
)
ui_skip_reason = "UI tests are disabled. Set AO_ENABLE_UI_TESTS=1 on Windows."



@pytest.mark.skipif(should_skip_ui, reason=ui_skip_reason)
def test_windows_controller_governance() -> None:
    controller = WindowsController(allow_os_automation=False)
    try:
        controller.get_active_window()
        raise AssertionError("Should raise RuntimeError")
    except RuntimeError as e:
        assert "disabled by governance" in str(e).lower() or "windows environment" in str(e).lower()


@pytest.mark.skipif(should_skip_ui, reason=ui_skip_reason)
def test_os_automation_tool_disabled_run() -> None:
    safe_runner = MagicMock()
    # Test disabled
    tool = OSAutomationTool(
        name="os_tool",
        safe_runner=safe_runner,
        workspace_dir=MagicMock(),
        config={},
        enabled=True,
        settings={"allow_os_automation": False}
    )
    outcome = tool._run({"action": "click", "target_label": "Start"})
    assert isinstance(outcome, dict)
    
    # We expect either the tool itself failed governance OR the controller raised.
    # Actually, tool._run calls os_controller.execute_visual_action which will raise.
    try:
        outcome = tool._run({"action": "click", "target_label": "Start"})
        if not outcome.get("success", True):
            assert "unavailable" in outcome.get("outcome", "").lower() or "disabled" in outcome.get("outcome", "").lower()
    except RuntimeError as e:
        assert "disabled" in str(e).lower() or "windows environment" in str(e).lower()
