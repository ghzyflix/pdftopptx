"""Desktop GUI for the PDF-to-PPTX converter using tkinter."""

import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from converter import convert_pdf_to_pptx


class PDFtoPPTXApp:
    """Main application window."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("PDF to PPTX Converter")
        self.root.geometry("620x400")
        self.root.resizable(False, False)
        self.converting = False
        self._build_ui()

    def _build_ui(self) -> None:
        # Configure style
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        # Header
        header_frame = ttk.Frame(self.root)
        header_frame.pack(fill=tk.X, padx=20, pady=(20, 5))

        title_label = ttk.Label(
            header_frame,
            text="PDF to PPTX Converter",
            font=("Helvetica", 16, "bold"),
        )
        title_label.pack(anchor=tk.W)

        subtitle_label = ttk.Label(
            header_frame,
            text="Convert PDF files to PowerPoint with preserved formatting",
            font=("Helvetica", 9),
        )
        subtitle_label.pack(anchor=tk.W, pady=(2, 0))

        # Separator
        ttk.Separator(self.root, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=20, pady=10)

        # Main content frame
        frame = ttk.Frame(self.root, padding=(20, 5))
        frame.pack(fill=tk.BOTH, expand=True)

        # Input file row
        ttk.Label(frame, text="Input PDF:", font=("Helvetica", 10)).grid(
            row=0, column=0, sticky=tk.W, pady=8
        )
        self.input_var = tk.StringVar()
        input_entry = ttk.Entry(frame, textvariable=self.input_var, width=48)
        input_entry.grid(row=0, column=1, padx=(10, 5), sticky=tk.EW)
        ttk.Button(frame, text="Browse...", command=self._browse_input).grid(
            row=0, column=2, padx=(5, 0)
        )

        # Output file row
        ttk.Label(frame, text="Output PPTX:", font=("Helvetica", 10)).grid(
            row=1, column=0, sticky=tk.W, pady=8
        )
        self.output_var = tk.StringVar()
        output_entry = ttk.Entry(frame, textvariable=self.output_var, width=48)
        output_entry.grid(row=1, column=1, padx=(10, 5), sticky=tk.EW)
        ttk.Button(frame, text="Browse...", command=self._browse_output).grid(
            row=1, column=2, padx=(5, 0)
        )

        # Options row
        options_frame = ttk.LabelFrame(frame, text="Options", padding=10)
        options_frame.grid(row=2, column=0, columnspan=3, sticky=tk.EW, pady=10)

        ttk.Label(options_frame, text="Fallback DPI:").grid(
            row=0, column=0, sticky=tk.W
        )
        self.dpi_var = tk.IntVar(value=300)
        dpi_spin = ttk.Spinbox(
            options_frame, from_=72, to=600, textvariable=self.dpi_var, width=6
        )
        dpi_spin.grid(row=0, column=1, padx=(5, 20), sticky=tk.W)

        ttk.Label(
            options_frame,
            text="(Higher DPI = better quality for complex pages, larger file)",
            font=("Helvetica", 8),
        ).grid(row=0, column=2, sticky=tk.W)

        # Convert button
        self.convert_btn = ttk.Button(
            frame, text="Convert", command=self._start_conversion
        )
        self.convert_btn.grid(row=3, column=0, columnspan=3, pady=(10, 5))

        # Progress bar
        self.progress = ttk.Progressbar(frame, length=540, mode="determinate")
        self.progress.grid(row=4, column=0, columnspan=3, pady=(5, 2), sticky=tk.EW)

        # Status label
        self.status_var = tk.StringVar(value="Ready")
        status_label = ttk.Label(
            frame, textvariable=self.status_var, font=("Helvetica", 9)
        )
        status_label.grid(row=5, column=0, columnspan=3, pady=(0, 5))

        # Configure column weight for stretching
        frame.columnconfigure(1, weight=1)

    def _browse_input(self) -> None:
        path = filedialog.askopenfilename(
            title="Select PDF File",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
        )
        if path:
            self.input_var.set(path)
            base = os.path.splitext(path)[0]
            self.output_var.set(base + ".pptx")

    def _browse_output(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Save PPTX As",
            defaultextension=".pptx",
            filetypes=[("PowerPoint files", "*.pptx"), ("All files", "*.*")],
        )
        if path:
            self.output_var.set(path)

    def _start_conversion(self) -> None:
        pdf_path = self.input_var.get().strip()
        pptx_path = self.output_var.get().strip()

        if not pdf_path:
            messagebox.showerror("Error", "Please select an input PDF file.")
            return
        if not os.path.isfile(pdf_path):
            messagebox.showerror("Error", f"File not found:\n{pdf_path}")
            return
        if not pptx_path:
            messagebox.showerror("Error", "Please specify an output path.")
            return

        # Ensure output directory exists
        out_dir = os.path.dirname(pptx_path)
        if out_dir and not os.path.isdir(out_dir):
            try:
                os.makedirs(out_dir, exist_ok=True)
            except OSError as e:
                messagebox.showerror(
                    "Error", f"Cannot create output directory:\n{e}"
                )
                return

        self.converting = True
        self.convert_btn.configure(state=tk.DISABLED)
        self.progress["value"] = 0
        self.status_var.set("Starting conversion...")

        thread = threading.Thread(
            target=self._run_conversion,
            args=(pdf_path, pptx_path, self.dpi_var.get()),
            daemon=True,
        )
        thread.start()

    def _run_conversion(self, pdf_path: str, pptx_path: str, dpi: int) -> None:
        try:
            convert_pdf_to_pptx(
                pdf_path,
                pptx_path,
                progress_callback=self._on_progress,
                fallback_dpi=dpi,
            )
            self.root.after(0, self._on_success, pptx_path)
        except Exception as e:
            self.root.after(0, self._on_error, str(e))

    def _on_progress(self, status_text: str, fraction: float) -> None:
        self.root.after(0, self._update_progress, status_text, fraction)

    def _update_progress(self, text: str, fraction: float) -> None:
        self.progress["value"] = fraction * 100
        self.status_var.set(text)

    def _on_success(self, output_path: str) -> None:
        self.converting = False
        self.convert_btn.configure(state=tk.NORMAL)
        self.progress["value"] = 100
        self.status_var.set("Conversion complete!")
        messagebox.showinfo("Success", f"PPTX saved to:\n{output_path}")

    def _on_error(self, error_msg: str) -> None:
        self.converting = False
        self.convert_btn.configure(state=tk.NORMAL)
        self.progress["value"] = 0
        self.status_var.set("Error occurred")
        messagebox.showerror("Conversion Error", error_msg)
