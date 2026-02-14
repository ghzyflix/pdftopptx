#!/usr/bin/env python3
"""PDF to PPTX Converter - Desktop Application.

Converts PDF files to PowerPoint presentations while preserving
text, fonts, images, colors, layout, and positioning.

Usage:
    GUI mode:   python main.py
    CLI mode:   python main.py input.pdf [output.pptx] [options]

CLI Options:
    --pages RANGE    Page range (e.g. "1-5", "1,3,7", "all")
    --dpi DPI        Fallback DPI for complex pages (default: 300)
    --hybrid         Enable hybrid mode (background image + text overlay)
"""

import argparse
import os
import sys


def run_gui() -> None:
    """Launch the GUI application."""
    import tkinter as tk
    from gui import PDFtoPPTXApp

    root = tk.Tk()

    root.update_idletasks()
    screen_w = root.winfo_screenwidth()
    screen_h = root.winfo_screenheight()
    win_w, win_h = 640, 520
    x = (screen_w - win_w) // 2
    y = (screen_h - win_h) // 2
    root.geometry(f"{win_w}x{win_h}+{x}+{y}")

    app = PDFtoPPTXApp(root)  # noqa: F841
    root.mainloop()


def run_cli(args: argparse.Namespace) -> None:
    """Run conversion from the command line."""
    from converter import convert_pdf_to_pptx

    pdf_path = args.input
    if not os.path.isfile(pdf_path):
        print(f"Error: File not found: {pdf_path}", file=sys.stderr)
        sys.exit(1)

    pptx_path = args.output
    if not pptx_path:
        pptx_path = os.path.splitext(pdf_path)[0] + ".pptx"

    out_dir = os.path.dirname(pptx_path)
    if out_dir and not os.path.isdir(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    def progress(text: str, fraction: float) -> None:
        bar_len = 30
        filled = int(bar_len * fraction)
        bar = "#" * filled + "-" * (bar_len - filled)
        print(f"\r[{bar}] {fraction*100:5.1f}% {text}", end="", flush=True)

    print(f"Converting: {pdf_path}")
    print(f"Output:     {pptx_path}")
    if args.hybrid:
        print("Mode:       Hybrid (background image + text overlay)")
    if args.pages and args.pages.lower() != "all":
        print(f"Pages:      {args.pages}")
    print()

    try:
        convert_pdf_to_pptx(
            pdf_path,
            pptx_path,
            progress_callback=progress,
            fallback_dpi=args.dpi,
            page_range=args.pages,
            hybrid_mode=args.hybrid,
        )
        print(f"\nDone! Saved to: {pptx_path}")
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    # If no arguments (or only script name), launch GUI
    if len(sys.argv) <= 1:
        run_gui()
        return

    # If first arg looks like a file path, use CLI mode
    parser = argparse.ArgumentParser(
        description="Convert PDF files to PowerPoint (PPTX) with preserved formatting.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n"
               "  python main.py                          # Launch GUI\n"
               "  python main.py report.pdf               # Convert to report.pptx\n"
               "  python main.py report.pdf out.pptx      # Specify output path\n"
               "  python main.py report.pdf --pages 1-5   # Convert pages 1-5\n"
               "  python main.py report.pdf --hybrid      # Pixel-perfect mode\n",
    )
    parser.add_argument("input", help="Input PDF file path")
    parser.add_argument("output", nargs="?", default=None, help="Output PPTX file path (default: same name as input)")
    parser.add_argument("--pages", default=None, help='Page range (e.g. "1-5", "1,3,7-10", "all")')
    parser.add_argument("--dpi", type=int, default=300, help="Fallback DPI for complex pages (default: 300)")
    parser.add_argument("--hybrid", action="store_true", help="Enable hybrid mode (pixel-perfect background + editable text)")

    args = parser.parse_args()
    run_cli(args)


if __name__ == "__main__":
    main()
