"""Coordinate and unit conversion utilities.

Converts between PDF points and EMU (English Metric Units) used by python-pptx.
1 inch = 72 PDF points = 914400 EMU
1 PDF point = 12700 EMU
"""

from typing import Tuple

PT_TO_EMU = 12700


def pt_to_emu(pt_value: float) -> int:
    """Convert PDF points to English Metric Units."""
    return int(pt_value * PT_TO_EMU)


def bbox_to_position_size(bbox: Tuple[float, float, float, float]) -> Tuple[int, int, int, int]:
    """Convert (x0, y0, x1, y1) in points to (left, top, width, height) in EMU."""
    x0, y0, x1, y1 = bbox
    return (
        pt_to_emu(x0),
        pt_to_emu(y0),
        max(pt_to_emu(x1 - x0), 1),
        max(pt_to_emu(y1 - y0), 1),
    )
