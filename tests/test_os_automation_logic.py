"""CI-safe unit tests for the OS Automation logic loop."""

import pytest
from unittest.mock import MagicMock

from os_controller.windows_controller import WindowsController

def test_progress_detection_loop() -> None:
    """Ensure that if the screen hash doesn't change, we abort after 3 attempts."""
    wc = WindowsController(allow_os_automation=True)
    # Give it a mock capture that always returns the same hash
    wc.screen_capture = MagicMock()
    wc.screen_capture.capture_screen.return_value = {
        "image": MagicMock(),
        "resolution": (1920, 1080),
        "timestamp": 12345.0,
        "hash": "same_hash_every_time",
        "offset": (0, 0)
    }
    
    wc.screen_reader = MagicMock()
    wc.screen_reader.analyze.return_value = {"elements": [], "state_summary": "", "warnings": []}
    
    # Mock recovery helpers to avoid real input
    wc._scroll_search = MagicMock()
    wc._dismiss_common_popups = MagicMock()
    wc.input_controller = MagicMock()
    
    # Give it a max attempts of 5 to see if it aborts at 3 due to no progress
    task = {"action": "click", "target": {"text": "Submit"}, "max_attempts": 5}
    
    result = wc.execute_task(task)
    
    assert result["success"] is False
    assert result["reason"] == "NO_PROGRESS"
    # Runs 4 times: 1 to get baseline, then 3 times seeing no change.
    assert len([s for s in result["steps"] if "Attempt" in s]) == 4


def test_visual_verification_success() -> None:
    """Ensure a changed hash results in success."""
    wc = WindowsController(allow_os_automation=True)
    wc.screen_capture = MagicMock()
    
    # Return hash A on first capture (before), hash B on second capture (after)
    wc.screen_capture.capture_screen.side_effect = [
        {"image": MagicMock(), "resolution": (100, 100), "timestamp": 1.0, "hash": "hashA", "offset": (0,0)},
        {"image": MagicMock(), "resolution": (100, 100), "timestamp": 2.0, "hash": "hashB", "offset": (0,0)},
    ]
    
    wc.screen_reader = MagicMock()
    wc.screen_reader.analyze.return_value = {
        "elements": [{"role": "text", "label": "Submit", "bbox": [0,0,10,10], "confidence": 1.0}],
        "state_summary": "", "warnings": []
    }
    
    wc._scroll_search = MagicMock()
    wc._dismiss_common_popups = MagicMock()
    wc.input_controller = MagicMock()
    
    task = {"action": "click", "target": {"text": "Submit"}, "max_attempts": 3}
    result = wc.execute_task(task)
    
    assert result["success"] is True
    assert result["reason"] is None
    assert wc.input_controller.click.called
