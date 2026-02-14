# PDF to PPTX Converter

A desktop application that converts PDF files to PowerPoint (PPTX) presentations with maximum fidelity — preserving text, fonts, images, colors, layout, vector shapes, hyperlinks, and background colors.

## Features

- **Text Preservation** — Extracts every text span with exact position, font name, size, bold/italic style, and RGB color
- **Image Extraction** — Full image extraction with SMASK transparency and CMYK-to-RGB conversion
- **Vector Shapes** — Reconstructs rectangles, lines, quads, and freeform line paths as native PPTX shapes
- **Hyperlink Preservation** — Extracts external URLs and internal page links, applies them as clickable hyperlinks in PPTX
- **Background Colors** — Detects page background colors and sets matching slide backgrounds
- **Rotated Text** — Detects text direction vectors and applies rotation to PPTX textboxes
- **Hybrid Mode** — Renders each page as a pixel-perfect background image with editable/searchable text overlaid on top
- **Page Range Selection** — Convert specific pages (e.g. `1-5`, `1,3,7-10`, `all`)
- **Fallback Rendering** — Pages with excessive vector complexity automatically fall back to high-DPI raster images
- **CLI Mode** — Full command-line interface with progress bar for scripting and batch workflows
- **Desktop GUI** — tkinter-based interface with file browsing, drag-and-drop/paste support, and live progress tracking

## Installation

### Requirements

- Python 3.8+

### Install Dependencies

```bash
pip install -r requirements.txt
```

Dependencies:
- [PyMuPDF](https://pymupdf.readthedocs.io/) — PDF parsing and rendering
- [python-pptx](https://python-pptx.readthedocs.io/) — PPTX generation
- [Pillow](https://pillow.readthedocs.io/) — Image format conversion (CMYK, etc.)

## Usage

### GUI Mode

Launch the graphical interface:

```bash
python main.py
```

1. Click **Browse** to select an input PDF file (or paste a path with Ctrl+V)
2. The output path auto-fills — adjust if needed
3. Set options:
   - **Page Range** — Which pages to convert (`all`, `1-5`, `1,3,7-10`)
   - **Fallback DPI** — Resolution for raster fallback on complex pages (default: 300)
   - **Hybrid Mode** — Check for pixel-perfect background with editable text overlay
4. Click **Convert**

### CLI Mode

Convert from the command line:

```bash
# Basic conversion
python main.py input.pdf

# Specify output path
python main.py input.pdf output.pptx

# Convert specific pages
python main.py input.pdf --pages 1-5

# Hybrid mode with custom DPI
python main.py input.pdf --hybrid --dpi 200

# All options
python main.py input.pdf output.pptx --pages 1,3,7-10 --dpi 300 --hybrid
```

#### CLI Options

| Option | Description | Default |
|---|---|---|
| `input` | Input PDF file path | (required) |
| `output` | Output PPTX file path | Same name as input |
| `--pages` | Page range (`"all"`, `"1-5"`, `"1,3,7-10"`) | `all` |
| `--dpi` | Fallback DPI for complex pages | `300` |
| `--hybrid` | Enable hybrid mode | Off |

## Conversion Modes

### Normal Mode (default)

Extracts text, images, and vector drawings as separate, editable PPTX elements. Text is fully editable, images are individual objects, and simple shapes are native PPTX shapes. Best for presentations where you need to edit content afterward.

### Hybrid Mode (`--hybrid`)

Renders each page as a high-resolution background image and overlays extracted text on top. This gives pixel-perfect visual fidelity (every gradient, shadow, and complex graphic is preserved exactly) while keeping text searchable and selectable in PowerPoint. Best when visual accuracy is the top priority.

### Fallback Mode (automatic)

Pages with more than 500 vector drawing paths are automatically rendered as full-page raster images. This prevents performance issues in PowerPoint from thousands of shape objects. The DPI setting controls the resolution of these fallback images.

## Architecture

```
main.py              Entry point — launches GUI or CLI
gui.py               tkinter desktop interface
converter.py         Pipeline orchestrator
pdf_extractor.py     PyMuPDF-based content extraction
pptx_builder.py      python-pptx slide generation
models.py            Intermediate data models
coord_utils.py       PDF points ↔ EMU coordinate conversion
font_mapper.py       PDF font name → system font mapping
```

### Data Flow

```
PDF File
 ├─ page.get_text("dict")     → text blocks/lines/spans with font, color, bbox
 ├─ page.get_image_info()     → images with positions and binary data
 ├─ page.get_cdrawings()      → vector paths with colors and line widths
 ├─ page.get_links()          → hyperlinks with bounding boxes
 └─ page.get_pixmap()         → full-page raster (fallback/hybrid)
         │
         ▼
   List[PageData]              intermediate representation (PDF points)
         │
         ▼
   Presentation()
 ├─ slide.background.fill     → background color
 ├─ shapes.add_picture()      → images at exact positions
 ├─ shapes.add_shape()        → rectangles and freeform paths
 └─ shapes.add_textbox()      → text with font, size, color, hyperlinks
         │
         ▼
   PPTX File
```

## License

MIT
