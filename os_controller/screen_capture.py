"""OS controller screen capture utility."""

from __future__ import annotations

import hashlib
import time
from typing import Any, TypedDict, cast

from PIL import Image

try:
    import mss
except ImportError:
    mss = None


class CaptureResult(TypedDict):
    """Result from capturing the screen or a window."""
    resolution: tuple[int, int]
    timestamp: float
    hash: str
    offset: tuple[int, int]


class ScreenCapture:
    """Manages high-speed cross-platform screen capture."""

    def __init__(self) -> None:
        self._mss_ctx = mss.mss() if mss else None
        self._last_hash: str | None = None

    def capture_screen(self, monitor_index: int = -1) -> CaptureResult | None:
        """Capture the screen.
        
        Args:
            monitor_index: -1 for all monitors combined, or 1-based index for specific monitor.
        """
        timestamp = time.time()
        offset = (0, 0)
        
        if self._mss_ctx:
            # mss uses 1-based index, or 0 for all monitors combined.
            idx = 0 if monitor_index == -1 else monitor_index
            try:
                monitors = self._mss_ctx.monitors
                if idx >= len(monitors):
                    idx = 0
                sct_mon = monitors[idx]
                sct_img = self._mss_ctx.grab(sct_mon)
                # Convert to PIL Image
                img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
                offset = (sct_mon["left"], sct_mon["top"])
            except Exception:
                return None
        else:
            # Fallback to ImageGrab
            try:
                from PIL import ImageGrab
                img = ImageGrab.grab(all_screens=True) if monitor_index == -1 else ImageGrab.grab()
            except Exception:
                return None

        if img is None:
            return None

        # Hash frame to see if it changed
        raw_bytes = img.tobytes()
        frame_hash = hashlib.md5(raw_bytes).hexdigest()
        self._last_hash = frame_hash

        return {
            "image": img,
            "resolution": cast(tuple[int, int], img.size),
            "timestamp": timestamp,
            "hash": frame_hash,
            "offset": offset,
        }

    def capture_active_window(self, window_manager: Any) -> CaptureResult | None:
        """Capture only the active window by fetching its bounding box."""
        timestamp = time.time()
        
        try:
            active = window_manager.get_active_window()
        except Exception:
            active = None
            
        if not active or not active.get("bbox"):
            # Fallback to full screen
            return self.capture_screen()
        
        # Expect bbox as (left, top, width, height) from the implementation we will do, or (left, top, right, bottom).
        # Let's standardize on (left, top, right, bottom) across the app to match ImageGrab.
        left, top, right, bottom = active["bbox"]
        width = right - left
        height = bottom - top
        
        # Guard against invalid bboxes
        if width <= 0 or height <= 0:
            return self.capture_screen()

        if self._mss_ctx:
            try:
                # mss grab takes a dict: {'left': x, 'top': y, 'width': w, 'height': h}
                box = {"left": int(left), "top": int(top), "width": int(width), "height": int(height)}
                sct_img = self._mss_ctx.grab(box)
                img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            except Exception:
                return None
        else:
            try:
                from PIL import ImageGrab
                img = ImageGrab.grab(bbox=(int(left), int(top), int(right), int(bottom)), all_screens=True)
            except Exception:
                return None
                
        if img is None:
            return None
            
        raw_bytes = img.tobytes()
        frame_hash = hashlib.md5(raw_bytes).hexdigest()
        self._last_hash = frame_hash
        
        return {
            "image": img,
            "resolution": cast(tuple[int, int], img.size),
            "timestamp": timestamp,
            "hash": frame_hash,
            "offset": (int(left), int(top)),
        }
