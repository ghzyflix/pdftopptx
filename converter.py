"""Converter pipeline orchestrating PDF extraction and PPTX generation."""

from typing import Callable, Optional

from pdf_extractor import extract_pdf
from pptx_builder import build_pptx


class ConversionProgress:
    """Track progress across extraction and building phases."""

    def __init__(self, callback: Optional[Callable[[str, float], None]] = None):
        self.callback = callback

    def update(self, phase: str, current: int, total: int) -> None:
        if not self.callback:
            return
        if phase == "extract":
            fraction = current / total * 0.5
            text = f"Extracting page {current}/{total}..."
        else:
            fraction = 0.5 + current / total * 0.5
            text = f"Building slide {current}/{total}..."
        self.callback(text, fraction)


def convert_pdf_to_pptx(
    pdf_path: str,
    pptx_path: str,
    progress_callback: Optional[Callable[[str, float], None]] = None,
    fallback_dpi: int = 300,
    page_range: Optional[str] = None,
    hybrid_mode: bool = False,
) -> None:
    """Convert a PDF file to PPTX with maximum fidelity.

    Args:
        pdf_path: Input PDF file path.
        pptx_path: Output PPTX file path.
        progress_callback: Called with (status_text, progress_fraction 0.0-1.0).
        fallback_dpi: DPI for raster fallback of complex pages.
        page_range: Page range string (e.g. "1-5", "1,3,7"). None = all pages.
        hybrid_mode: If True, render pages as background images with text overlay.
    """
    progress = ConversionProgress(progress_callback)

    # Phase 1: Extract content from PDF
    pages = extract_pdf(
        pdf_path,
        progress_callback=lambda cur, tot: progress.update("extract", cur, tot),
        fallback_dpi=fallback_dpi,
        page_range=page_range,
        hybrid_mode=hybrid_mode,
    )

    if not pages:
        raise ValueError("No pages found in the PDF file.")

    # Phase 2: Build PPTX from extracted content
    build_pptx(
        pages,
        pptx_path,
        progress_callback=lambda cur, tot: progress.update("build", cur, tot),
    )
