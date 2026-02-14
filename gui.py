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
        self.root.geometry("640x520")
        self.root.resizable(False, False)
        self.converting = False
        self._build_ui()
        self._setup_drag_and_drop()

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
        ttk.Separator(self.root, orient=tk.HORIZONTAL).pack(
            fill=tk.X, padx=20, pady=10
        )

        # Main content frame
        frame = ttk.Frame(self.root, padding=(20, 5))
        frame.pack(fill=tk.BOTH, expand=True)

        # --- Drop zone ---
        self.drop_frame = tk.Frame(
            frame, bg="#e8f0fe", highlightbackground="#4285f4",
            highlightthickness=2, height=50,
        )
        self.drop_frame.grid(row=0, column=0, columnspan=3, sticky=tk.EW, pady=(0, 10))
        self.drop_frame.grid_propagate(False)
        self.drop_label = tk.Label(
            self.drop_frame,
            text="Drop a PDF file here or use Browse below",
            bg="#e8f0fe", fg="#4285f4", font=("Helvetica", 10),
        )
        self.drop_label.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        # Input file row
        ttk.Label(frame, text="Input PDF:", font=("Helvetica", 10)).grid(
            row=1, column=0, sticky=tk.W, pady=6
        )
        self.input_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.input_var, width=48).grid(
            row=1, column=1, padx=(10, 5), sticky=tk.EW
        )
        ttk.Button(frame, text="Browse...", command=self._browse_input).grid(
            row=1, column=2, padx=(5, 0)
        )

        # Output file row
        ttk.Label(frame, text="Output PPTX:", font=("Helvetica", 10)).grid(
            row=2, column=0, sticky=tk.W, pady=6
        )
        self.output_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.output_var, width=48).grid(
            row=2, column=1, padx=(10, 5), sticky=tk.EW
        )
        ttk.Button(frame, text="Browse...", command=self._browse_output).grid(
            row=2, column=2, padx=(5, 0)
        )

        # Options frame
        options_frame = ttk.LabelFrame(frame, text="Options", padding=10)
        options_frame.grid(row=3, column=0, columnspan=3, sticky=tk.EW, pady=8)

        # Row 0: Page range
        ttk.Label(options_frame, text="Page Range:").grid(
            row=0, column=0, sticky=tk.W, pady=3
        )
        self.page_range_var = tk.StringVar(value="all")
        page_entry = ttk.Entry(
            options_frame, textvariable=self.page_range_var, width=20
        )
        page_entry.grid(row=0, column=1, padx=(5, 10), sticky=tk.W)
        ttk.Label(
            options_frame,
            text='e.g. "all", "1-5", "1,3,7-10"',
            font=("Helvetica", 8),
        ).grid(row=0, column=2, sticky=tk.W)

        # Row 1: DPI
        ttk.Label(options_frame, text="Fallback DPI:").grid(
            row=1, column=0, sticky=tk.W, pady=3
        )
        self.dpi_var = tk.IntVar(value=300)
        dpi_spin = ttk.Spinbox(
            options_frame, from_=72, to=600, textvariable=self.dpi_var, width=6
        )
        dpi_spin.grid(row=1, column=1, padx=(5, 10), sticky=tk.W)
        ttk.Label(
            options_frame,
            text="(Higher = better quality, larger file)",
            font=("Helvetica", 8),
        ).grid(row=1, column=2, sticky=tk.W)

        # Row 2: Hybrid mode checkbox
        self.hybrid_var = tk.BooleanVar(value=False)
        hybrid_check = ttk.Checkbutton(
            options_frame,
            text="Hybrid Mode (pixel-perfect background + editable text overlay)",
            variable=self.hybrid_var,
        )
        hybrid_check.grid(row=2, column=0, columnspan=3, sticky=tk.W, pady=(6, 0))

        # Convert button
        self.convert_btn = ttk.Button(
            frame, text="Convert", command=self._start_conversion
        )
        self.convert_btn.grid(row=4, column=0, columnspan=3, pady=(10, 5))

        # Progress bar
        self.progress = ttk.Progressbar(frame, length=560, mode="determinate")
        self.progress.grid(row=5, column=0, columnspan=3, pady=(5, 2), sticky=tk.EW)

        # Status label
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(
            frame, textvariable=self.status_var, font=("Helvetica", 9)
        ).grid(row=6, column=0, columnspan=3, pady=(0, 5))

        # Configure column weight
        frame.columnconfigure(1, weight=1)

    def _setup_drag_and_drop(self) -> None:
        """Set up drag-and-drop support via tkinter DnD or manual paste fallback."""
        # Try to use tkdnd if available, otherwise bind keyboard paste
        try:
            self.root.tk.eval("package require tkdnd")
            self._setup_tkdnd()
        except tk.TclError:
            # tkdnd not available, use paste shortcut as fallback
            self.root.bind("<Control-v>", self._on_paste)
            self.drop_label.configure(
                text="Paste a PDF path (Ctrl+V) or use Browse below"
            )

    def _setup_tkdnd(self) -> None:
        """Register TkDND drop targets."""
        try:
            self.root.tk.eval(
                f'tkdnd::drop_target register {self.drop_frame} *'
            )
            self.root.tk.eval(
                f'bind {self.drop_frame} <<Drop>> {{set ::_dropped_data %D}}'
            )
        except tk.TclError:
            pass

    def _on_paste(self, event) -> None:
        """Handle Ctrl+V paste for file paths."""
        try:
            clipboard = self.root.clipboard_get()
            path = clipboard.strip().strip('"').strip("'")
            if path.lower().endswith(".pdf") and os.path.isfile(path):
                self._set_input_file(path)
        except tk.TclError:
            pass

    def _set_input_file(self, path: str) -> None:
        """Set input file and auto-fill output path."""
        self.input_var.set(path)
        base = os.path.splitext(path)[0]
        self.output_var.set(base + ".pptx")
        self.drop_label.configure(
            text=f"Loaded: {os.path.basename(path)}"
        )

    def _browse_input(self) -> None:
        path = filedialog.askopenfilename(
            title="Select PDF File",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
        )
        if path:
            self._set_input_file(path)

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

        page_range = self.page_range_var.get().strip()
        if not page_range:
            page_range = None

        thread = threading.Thread(
            target=self._run_conversion,
            args=(pdf_path, pptx_path, self.dpi_var.get(),
                  page_range, self.hybrid_var.get()),
            daemon=True,
        )
        thread.start()

    def _run_conversion(
        self, pdf_path: str, pptx_path: str, dpi: int,
        page_range: str, hybrid_mode: bool,
    ) -> None:
        try:
            convert_pdf_to_pptx(
                pdf_path,
                pptx_path,
                progress_callback=self._on_progress,
                fallback_dpi=dpi,
                page_range=page_range,
                hybrid_mode=hybrid_mode,
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
