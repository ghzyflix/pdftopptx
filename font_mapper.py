"""Map PDF font names to system font names suitable for PPTX."""

import re

_FONT_MAP = {
    "times": "Times New Roman",
    "timesnewroman": "Times New Roman",
    "timesnewromanps": "Times New Roman",
    "timesnewromanpsmt": "Times New Roman",
    "arial": "Arial",
    "arialmt": "Arial",
    "helvetica": "Arial",
    "helveticaneue": "Arial",
    "courier": "Courier New",
    "couriernew": "Courier New",
    "couriernewpsmt": "Courier New",
    "calibri": "Calibri",
    "cambria": "Cambria",
    "verdana": "Verdana",
    "tahoma": "Tahoma",
    "georgia": "Georgia",
    "garamond": "Garamond",
    "symbol": "Symbol",
    "zapfdingbats": "Wingdings",
    "wingdings": "Wingdings",
    "palatino": "Palatino Linotype",
    "palatinolinotype": "Palatino Linotype",
    "bookantiqua": "Book Antiqua",
    "trebuchetms": "Trebuchet MS",
    "comicsansms": "Comic Sans MS",
    "impact": "Impact",
    "lucidaconsole": "Lucida Console",
    "lucidasansunicode": "Lucida Sans Unicode",
    "microsoftsansserif": "Microsoft Sans Serif",
    "segoeui": "Segoe UI",
    "consolas": "Consolas",
    "dejavusans": "DejaVu Sans",
    "dejavuserif": "DejaVu Serif",
    "dejavusansmono": "DejaVu Sans Mono",
    "liberationsans": "Liberation Sans",
    "liberationserif": "Liberation Serif",
    "liberationmono": "Liberation Mono",
    "noto": "Noto Sans",
    "notosans": "Noto Sans",
    "notoserif": "Noto Serif",
    "roboto": "Roboto",
    "opensans": "Open Sans",
    "lato": "Lato",
    "sourcesanspro": "Source Sans Pro",
    "montserrat": "Montserrat",
}

_STYLE_SUFFIXES = re.compile(
    r"[-,]?\s*(bold|italic|oblique|regular|medium|light|"
    r"semibold|demibold|black|thin|condensed|narrow|mt|ps|"
    r"boldmt|bolditalicmt|italicmt|extrabold|ultralight)\s*",
    re.IGNORECASE,
)


def _strip_prefix(font_name: str) -> str:
    """Remove the 6-char subset prefix like 'ABCDEF+' from PDF font names."""
    if len(font_name) > 7 and font_name[6] == "+":
        return font_name[7:]
    return font_name


def map_font(pdf_font_name: str) -> str:
    """Map a PDF font name to a system font name for PPTX."""
    name = _strip_prefix(pdf_font_name)

    normalized = name.lower().replace(" ", "").replace("-", "").replace("_", "")
    if normalized in _FONT_MAP:
        return _FONT_MAP[normalized]

    base_name = _STYLE_SUFFIXES.sub("", normalized).strip()
    if base_name in _FONT_MAP:
        return _FONT_MAP[base_name]

    # Return cleaned name as best effort
    clean = re.sub(r"[-](Bold|Italic|BoldItalic|Regular|Medium|Light)$", "", name)
    return clean if clean else name
