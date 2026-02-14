"""Data models for the PDF-to-PPTX converter intermediate representation.

All coordinates are in PDF points (72 points = 1 inch) with origin at top-left.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass
class HyperlinkInfo:
    """A hyperlink associated with a region on a page."""
    bbox: Tuple[float, float, float, float]
    uri: str
    is_external: bool = True


@dataclass
class TextSpan:
    """A run of text with uniform formatting."""
    text: str
    x: float
    y: float
    bbox: Tuple[float, float, float, float]
    font_name: str
    font_size: float
    color_rgb: Tuple[int, int, int]
    is_bold: bool
    is_italic: bool
    is_superscript: bool = False
    hyperlink: Optional[str] = None


@dataclass
class TextLine:
    """A line of text composed of spans."""
    bbox: Tuple[float, float, float, float]
    spans: List[TextSpan] = field(default_factory=list)
    wmode: int = 0
    direction: Tuple[float, float] = (1.0, 0.0)


@dataclass
class TextBlock:
    """A block (paragraph) of text composed of lines."""
    bbox: Tuple[float, float, float, float]
    lines: List[TextLine] = field(default_factory=list)


@dataclass
class ImageElement:
    """An image placed on a page."""
    bbox: Tuple[float, float, float, float]
    image_bytes: bytes
    image_ext: str
    original_width: int
    original_height: int


@dataclass
class DrawingPath:
    """A vector drawing path with visual properties."""
    rect: Tuple[float, float, float, float]
    items: list
    fill_color: Optional[Tuple[float, float, float]] = None
    stroke_color: Optional[Tuple[float, float, float]] = None
    line_width: float = 0
    dashes: Optional[str] = None
    close_path: bool = False
    line_join: int = 0
    line_cap: Tuple = (0,)
    fill_opacity: float = 1.0
    stroke_opacity: float = 1.0


@dataclass
class PageData:
    """All extracted content from a single PDF page."""
    page_number: int
    width: float
    height: float
    text_blocks: List[TextBlock] = field(default_factory=list)
    images: List[ImageElement] = field(default_factory=list)
    drawings: List[DrawingPath] = field(default_factory=list)
    hyperlinks: List[HyperlinkInfo] = field(default_factory=list)
    fallback_image: Optional[bytes] = None
    background_color: Optional[Tuple[int, int, int]] = None
    # For hybrid mode: high-res background + text overlay
    background_render: Optional[bytes] = None
