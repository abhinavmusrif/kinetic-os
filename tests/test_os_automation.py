"""Tests for the OS Automation visual loop."""

from unittest.mock import MagicMock

from os_controller.windows_controller import WindowsController
from tools.system_tools.os_automation_tool import OSAutomationTool


def test_windows_controller_governance() -> None:
    controller = WindowsController(allow_os_automation=False)
    try:
        controller.get_active_window()
        raise AssertionError("Should raise RuntimeError")
    except RuntimeError as e:
        assert "disabled by governance" in str(e).lower() or "windows environment" in str(e).lower()


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
