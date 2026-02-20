"""Native Windows Accessibility (UIAutomation) tree parser.

Walks the UI Automation tree of the currently active window and extracts
all interactable elements (buttons, edit controls, links, list items, text)
with their exact bounding box coordinates.  Compresses results into a
numbered text list for LLM consumption — orders of magnitude faster than
screenshot → OCR.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger("ao.ui_tree")

# Lazy-load uiautomation to avoid hard crash on Linux / CI
try:
    import uiautomation as auto
except ImportError:
    auto = None

# Control types we consider "interactable"
_INTERACTABLE_TYPES = {
    "ButtonControl",
    "EditControl",
    "HyperlinkControl",
    "ListItemControl",
    "MenuItemControl",
    "TabItemControl",
    "CheckBoxControl",
    "RadioButtonControl",
    "ComboBoxControl",
    "TextControl",
    "TreeItemControl",
    "DataItemControl",
}

# Human-readable short type labels
_TYPE_LABEL_MAP = {
    "ButtonControl": "Button",
    "EditControl": "Input",
    "HyperlinkControl": "Link",
    "ListItemControl": "ListItem",
    "MenuItemControl": "MenuItem",
    "TabItemControl": "Tab",
    "CheckBoxControl": "Checkbox",
    "RadioButtonControl": "Radio",
    "ComboBoxControl": "Dropdown",
    "TextControl": "Text",
    "TreeItemControl": "TreeItem",
    "DataItemControl": "DataItem",
}


@dataclass
class UITreeElement:
    """A single interactable element extracted from the UI tree."""

    id: int
    element_type: str
    label: str
    center_x: int
    center_y: int
    width: int
    height: int


def is_available() -> bool:
    """Check if the uiautomation library is usable."""
    return auto is not None


def parse_active_window(max_elements: int = 120, timeout_ms: int = 3000) -> list[UITreeElement]:
    """Walk the UI tree of the active window and return interactable elements.

    Args:
        max_elements: Stop after collecting this many elements to stay fast.
        timeout_ms: Maximum time in milliseconds before aborting the walk.

    Returns:
        List of UITreeElement with bounding box data.
    """
    if auto is None:
        logger.warning("uiautomation not installed — UI tree unavailable")
        return []

    deadline = time.perf_counter() + timeout_ms / 1000.0
    elements: list[UITreeElement] = []

    try:
        # Get the foreground window's automation element
        root = auto.GetForegroundControl()
        if root is None:
            logger.warning("No foreground window detected")
            return []

        _walk(root, elements, max_elements, deadline, id_counter=[0])
    except Exception as exc:
        logger.warning("UI tree walk failed: %s", exc)

    return elements


def _walk(
    control: Any,
    out: list[UITreeElement],
    max_elements: int,
    deadline: float,
    id_counter: list[int],
    depth: int = 0,
) -> None:
    """Recursive depth-first walk of the UI automation tree."""
    if len(out) >= max_elements or time.perf_counter() > deadline:
        return

    # Cap depth to avoid infinite recursion in broken trees
    if depth > 25:
        return

    control_type = control.ControlTypeName

    if control_type in _INTERACTABLE_TYPES:
        try:
            rect = control.BoundingRectangle
            # Skip elements with zero-size or off-screen
            w = rect.right - rect.left
            h = rect.bottom - rect.top
            if w > 0 and h > 0 and rect.left >= -10 and rect.top >= -10:
                label = (control.Name or "").strip()
                if not label and control_type == "EditControl":
                    label = "(text field)"
                if label or control_type != "TextControl":
                    cx = rect.left + w // 2
                    cy = rect.top + h // 2
                    elem = UITreeElement(
                        id=id_counter[0],
                        element_type=_TYPE_LABEL_MAP.get(control_type, control_type),
                        label=label or "(unlabeled)",
                        center_x=cx,
                        center_y=cy,
                        width=w,
                        height=h,
                    )
                    out.append(elem)
                    id_counter[0] += 1
        except Exception:
            pass  # Some controls don't expose BoundingRectangle

    # Recurse into children
    try:
        child = control.GetFirstChildControl()
        while child and len(out) < max_elements and time.perf_counter() < deadline:
            _walk(child, out, max_elements, deadline, id_counter, depth + 1)
            child = child.GetNextSiblingControl()
    except Exception:
        pass


def build_tree_map(elements: list[UITreeElement] | None = None) -> str:
    """Build a numbered text map from UI tree elements.

    If *elements* is None, parses the active window on the fly.

    Returns:
        A string like:
        [ID: 0] Button 'Submit' @ (x:500, y:100)
        [ID: 1] Input '(text field)' @ (x:400, y:200)
    """
    if elements is None:
        elements = parse_active_window()

    if not elements:
        return "(No interactable elements found in UI tree)"

    lines: list[str] = []
    for el in elements:
        lines.append(
            f"[ID: {el.id}] {el.element_type} '{el.label}' @ (x:{el.center_x}, y:{el.center_y})"
        )
    return "\n".join(lines)


def get_element_coords(elements: list[UITreeElement], element_id: int) -> tuple[int, int] | None:
    """Look up center coordinates for a given element ID."""
    for el in elements:
        if el.id == element_id:
            return (el.center_x, el.center_y)
    return None
