#!/usr/bin/env python3
"""PDF to PPTX Converter - Desktop Application.

Converts PDF files to PowerPoint presentations while preserving
text, fonts, images, colors, layout, and positioning.

Usage:
    python main.py
"""

import sys
import tkinter as tk

from gui import PDFtoPPTXApp


def main() -> None:
    root = tk.Tk()

    # Center window on screen
    root.update_idletasks()
    screen_w = root.winfo_screenwidth()
    screen_h = root.winfo_screenheight()
    win_w, win_h = 620, 400
    x = (screen_w - win_w) // 2
    y = (screen_h - win_h) // 2
    root.geometry(f"{win_w}x{win_h}+{x}+{y}")

    app = PDFtoPPTXApp(root)  # noqa: F841
    root.mainloop()


if __name__ == "__main__":
    main()
