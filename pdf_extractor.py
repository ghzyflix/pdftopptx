"""PDF content extraction using PyMuPDF (fitz).

Extracts text (with fonts, colors, positions), images, vector drawings,
hyperlinks, and background colors from each page of a PDF file.
"""

import fitz
from io import BytesIO
from typing import Callable, List, Optional, Set

from models import (
    DrawingPath,
    HyperlinkInfo,
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


def parse_page_range(page_range: str, total_pages: int) -> List[int]:
    """Parse a page range string into a list of 0-based page indices.

    Supports formats like: "1-5", "1,3,5", "1-3,7,10-12", "all"
    Pages are 1-based in input, returned as 0-based indices.
    """
    if not page_range or page_range.strip().lower() == "all":
        return list(range(total_pages))

    pages: Set[int] = set()
    for part in page_range.split(","):
        part = part.strip()
        if "-" in part:
            try:
                start, end = part.split("-", 1)
                start = max(1, int(start.strip()))
                end = min(total_pages, int(end.strip()))
                for p in range(start, end + 1):
                    pages.add(p - 1)
            except ValueError:
                continue
        else:
            try:
                p = int(part)
                if 1 <= p <= total_pages:
                    pages.add(p - 1)
            except ValueError:
                continue

    return sorted(pages)


def extract_pdf(
    pdf_path: str,
    progress_callback: Optional[Callable[[int, int], None]] = None,
    use_drawing_extraction: bool = True,
    drawing_fallback_threshold: int = 500,
    fallback_dpi: int = 300,
    page_range: Optional[str] = None,
    hybrid_mode: bool = False,
) -> List[PageData]:
    """Extract all content from a PDF file.

    Args:
        pdf_path: Path to the PDF file.
        progress_callback: Called with (current_page, total_pages).
        use_drawing_extraction: Whether to attempt vector drawing extraction.
        drawing_fallback_threshold: If drawings exceed this count per page,
            fall back to a full-page raster image for that page.
        fallback_dpi: DPI for raster fallback rendering.
        page_range: Page range string (e.g. "1-5", "1,3,7"). None = all pages.
        hybrid_mode: If True, render each page as a background image AND
            extract text as an overlay for searchability/editability.

    Returns:
        List of PageData, one per page.
    """
    doc = fitz.open(pdf_path)
    total_doc_pages = len(doc)

    page_indices = parse_page_range(page_range, total_doc_pages)
    if not page_indices:
        doc.close()
        return []

    pages: List[PageData] = []
    total = len(page_indices)

    for count, page_idx in enumerate(page_indices):
        page = doc[page_idx]
        page_data = _extract_page(
            page,
            page_idx,
            doc,
            use_drawing_extraction,
            drawing_fallback_threshold,
            fallback_dpi,
            hybrid_mode,
        )
        pages.append(page_data)
        if progress_callback:
            progress_callback(count + 1, total)

    doc.close()
    return pages


def _extract_page(
    page,
    page_idx: int,
    doc,
    use_drawings: bool,
    drawing_threshold: int,
    fallback_dpi: int,
    hybrid_mode: bool,
) -> PageData:
    """Extract all content from a single PDF page."""
    rect = page.rect
    page_data = PageData(
        page_number=page_idx,
        width=rect.width,
        height=rect.height,
    )

    # Background color extraction
    page_data.background_color = _extract_background_color(page)

    # Hyperlink extraction
    page_data.hyperlinks = _extract_hyperlinks(page)

    # Text extraction (always needed for hybrid mode and normal mode)
    page_data.text_blocks = _extract_text(page)

    # Assign hyperlinks to text spans
    _assign_hyperlinks_to_spans(page_data)

    if hybrid_mode:
        # Hybrid mode: render full page as background, keep text as overlay
        page_data.background_render = _render_page_as_image(page, fallback_dpi)
        # Clear images and drawings since the background render covers them
        page_data.images = []
        page_data.drawings = []
        return page_data

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
            page_data.text_blocks = []
            page_data.images = []
            page_data.drawings = []
        else:
            page_data.drawings = _extract_drawings(drawings)

    return page_data


def _extract_background_color(page) -> tuple:
    """Detect the background color of a page.

    Checks for a filled rectangle covering most of the page in the
    page's drawing commands. Falls back to white.
    """
    try:
        drawings = page.get_cdrawings()
    except Exception:
        return None

    page_area = page.rect.width * page.rect.height
    if page_area <= 0:
        return None

    for path in drawings:
        if not path.get("fill"):
            continue
        prect = path.get("rect")
        if not prect:
            continue
        pw = prect[2] - prect[0]
        ph = prect[3] - prect[1]
        path_area = pw * ph
        # If a filled rect covers >= 90% of the page, it's likely the background
        if path_area >= page_area * 0.9:
            fill = path["fill"]
            r = max(0, min(255, int(fill[0] * 255)))
            g = max(0, min(255, int(fill[1] * 255)))
            b = max(0, min(255, int(fill[2] * 255)))
            # Skip white backgrounds (default anyway)
            if (r, g, b) == (255, 255, 255):
                return None
            return (r, g, b)

    return None


def _extract_hyperlinks(page) -> List[HyperlinkInfo]:
    """Extract all hyperlinks from a page."""
    links: List[HyperlinkInfo] = []

    for link in page.get_links():
        uri = link.get("uri", "")
        kind = link.get("kind", 0)

        # kind 2 = URI link (external), kind 1 = goto (internal page link)
        if kind == 2 and uri:
            bbox = link.get("from")
            if bbox:
                links.append(HyperlinkInfo(
                    bbox=(bbox.x0, bbox.y0, bbox.x1, bbox.y1),
                    uri=uri,
                    is_external=True,
                ))
        elif kind == 1:
            # Internal page link - store as #page=N
            target_page = link.get("page", 0)
            bbox = link.get("from")
            if bbox:
                links.append(HyperlinkInfo(
                    bbox=(bbox.x0, bbox.y0, bbox.x1, bbox.y1),
                    uri=f"#page={target_page + 1}",
                    is_external=False,
                ))

    return links


def _assign_hyperlinks_to_spans(page_data: PageData) -> None:
    """Assign hyperlink URIs to text spans based on bbox overlap."""
    if not page_data.hyperlinks:
        return

    for block in page_data.text_blocks:
        for line in block.lines:
            for span in line.spans:
                sx0, sy0, sx1, sy1 = span.bbox
                for link in page_data.hyperlinks:
                    lx0, ly0, lx1, ly1 = link.bbox
                    # Check overlap
                    if sx0 < lx1 and sx1 > lx0 and sy0 < ly1 and sy1 > ly0:
                        span.hyperlink = link.uri
                        break


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

        bbox_key = (xref, tuple(bbox))
        if bbox_key in seen_xrefs:
            continue
        seen_xrefs.add(bbox_key)

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
