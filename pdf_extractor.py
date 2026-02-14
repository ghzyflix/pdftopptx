"""PDF content extraction using PyMuPDF (fitz).

Extracts text (with fonts, colors, positions), images, and vector drawings
from each page of a PDF file.
"""

import fitz
from io import BytesIO
from typing import Callable, List, Optional

from models import (
    DrawingPath,
    ImageElement,
    PageData,
    TextBlock,
    TextLine,
    TextSpan,
)

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


def extract_pdf(
    pdf_path: str,
    progress_callback: Optional[Callable[[int, int], None]] = None,
    use_drawing_extraction: bool = True,
    drawing_fallback_threshold: int = 500,
    fallback_dpi: int = 300,
) -> List[PageData]:
    """Extract all content from a PDF file.

    Args:
        pdf_path: Path to the PDF file.
        progress_callback: Called with (current_page, total_pages).
        use_drawing_extraction: Whether to attempt vector drawing extraction.
        drawing_fallback_threshold: If drawings exceed this count per page,
            fall back to a full-page raster image for that page.
        fallback_dpi: DPI for raster fallback rendering.

    Returns:
        List of PageData, one per page.
    """
    doc = fitz.open(pdf_path)
    pages: List[PageData] = []
    total = len(doc)

    for page_idx in range(total):
        page = doc[page_idx]
        page_data = _extract_page(
            page,
            page_idx,
            doc,
            use_drawing_extraction,
            drawing_fallback_threshold,
            fallback_dpi,
        )
        pages.append(page_data)
        if progress_callback:
            progress_callback(page_idx + 1, total)

    doc.close()
    return pages


def _extract_page(
    page,
    page_idx: int,
    doc,
    use_drawings: bool,
    drawing_threshold: int,
    fallback_dpi: int,
) -> PageData:
    """Extract all content from a single PDF page."""
    rect = page.rect
    page_data = PageData(
        page_number=page_idx,
        width=rect.width,
        height=rect.height,
    )

    # Text extraction
    page_data.text_blocks = _extract_text(page)

    # Image extraction
    page_data.images = _extract_images(page, doc)

    # Drawing extraction
    if use_drawings:
        try:
            drawings = page.get_cdrawings()
        except Exception:
            drawings = []

        if len(drawings) > drawing_threshold:
            page_data.fallback_image = _render_page_as_image(page, fallback_dpi)
            # When using fallback, clear extracted text/images since the
            # raster image covers everything
            page_data.text_blocks = []
            page_data.images = []
            page_data.drawings = []
        else:
            page_data.drawings = _extract_drawings(drawings)

    return page_data


def _extract_text(page) -> List[TextBlock]:
    """Extract text with full formatting using the 'dict' option."""
    flags = fitz.TEXTFLAGS_TEXT
    try:
        data = page.get_text("dict", flags=flags)
    except Exception:
        return []

    blocks: List[TextBlock] = []

    for block in data.get("blocks", []):
        if block.get("type") != 0:
            continue

        text_block = TextBlock(bbox=tuple(block["bbox"]), lines=[])

        for line in block.get("lines", []):
            text_line = TextLine(
                bbox=tuple(line["bbox"]),
                wmode=line.get("wmode", 0),
                direction=tuple(line.get("dir", (1.0, 0.0))),
                spans=[],
            )

            for span in line.get("spans", []):
                text = span.get("text", "")
                if not text:
                    continue

                span_flags = span.get("flags", 0)
                color_int = span.get("color", 0)
                r = (color_int >> 16) & 0xFF
                g = (color_int >> 8) & 0xFF
                b = color_int & 0xFF

                origin = span.get("origin", (0, 0))

                text_span = TextSpan(
                    text=text,
                    x=origin[0],
                    y=origin[1],
                    bbox=tuple(span["bbox"]),
                    font_name=span.get("font", "Arial"),
                    font_size=span.get("size", 12.0),
                    color_rgb=(r, g, b),
                    is_bold=bool(span_flags & 16),
                    is_italic=bool(span_flags & 2),
                    is_superscript=bool(span_flags & 1),
                )
                text_line.spans.append(text_span)

            if text_line.spans:
                text_block.lines.append(text_line)

        if text_block.lines:
            blocks.append(text_block)

    return blocks


def _extract_images(page, doc) -> List[ImageElement]:
    """Extract all images with their positions and binary data."""
    images: List[ImageElement] = []

    try:
        image_infos = page.get_image_info(xrefs=True)
    except Exception:
        return images

    seen_xrefs = set()

    for info in image_infos:
        xref = info.get("xref", 0)
        bbox = info.get("bbox")

        if not bbox or xref == 0:
            continue

        # Skip duplicate xrefs on the same page (same image placed multiple times
        # is handled by having multiple infos with different bboxes)
        bbox_key = (xref, tuple(bbox))
        if bbox_key in seen_xrefs:
            continue
        seen_xrefs.add(bbox_key)

        # Skip tiny images (likely artifacts)
        bw = bbox[2] - bbox[0]
        bh = bbox[3] - bbox[1]
        if bw < 1 or bh < 1:
            continue

        try:
            img_data = doc.extract_image(xref)
            if not img_data or not img_data.get("image"):
                continue

            image_bytes = img_data["image"]
            image_ext = img_data.get("ext", "png")

            # Handle SMASK (transparency mask)
            smask_xref = img_data.get("smask", 0)
            if smask_xref and smask_xref > 0:
                try:
                    pix = fitz.Pixmap(doc, xref)
                    mask_pix = fitz.Pixmap(doc, smask_xref)
                    if pix.width == mask_pix.width and pix.height == mask_pix.height:
                        pix = fitz.Pixmap(pix, mask_pix)
                        image_bytes = pix.tobytes("png")
                        image_ext = "png"
                    pix = None
                    mask_pix = None
                except Exception:
                    pass

            # Convert CMYK to RGB if needed
            if HAS_PIL and image_ext in ("jpeg", "jpg"):
                try:
                    img = Image.open(BytesIO(image_bytes))
                    if img.mode == "CMYK":
                        img = img.convert("RGB")
                        buf = BytesIO()
                        img.save(buf, format="PNG")
                        image_bytes = buf.getvalue()
                        image_ext = "png"
                except Exception:
                    pass

            images.append(
                ImageElement(
                    bbox=tuple(bbox),
                    image_bytes=image_bytes,
                    image_ext=image_ext,
                    original_width=info.get("width", 0),
                    original_height=info.get("height", 0),
                )
            )
        except Exception:
            continue

    return images


def _extract_drawings(drawings: list) -> List[DrawingPath]:
    """Convert PyMuPDF drawing paths to our model."""
    result: List[DrawingPath] = []

    for path in drawings:
        rect = path.get("rect")
        if not rect:
            continue

        items = path.get("items", [])
        if not items:
            continue

        dp = DrawingPath(
            rect=tuple(rect),
            items=items,
            fill_color=tuple(path["fill"]) if path.get("fill") else None,
            stroke_color=tuple(path["color"]) if path.get("color") else None,
            line_width=path.get("width", 0),
            dashes=path.get("dashes"),
            close_path=path.get("closePath", False),
            line_join=path.get("lineJoin", 0),
            line_cap=path.get("lineCap", (0,)),
            fill_opacity=path.get("fill_opacity", 1.0),
            stroke_opacity=path.get("stroke_opacity", 1.0),
        )
        result.append(dp)

    return result


def _render_page_as_image(page, dpi: int = 300) -> bytes:
    """Render entire page as a high-resolution PNG."""
    mat = fitz.Matrix(dpi / 72, dpi / 72)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    return pix.tobytes("png")
