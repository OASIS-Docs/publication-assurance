"""Measure the type sizes a PDF actually prints, from its text layer.

Every text span is classed as footer (below the 25mm bottom margin), header
(above the 25mm top margin), code (a monospace face) or body (anything else
in the text column). Each class reports the size that carries the most
characters, so a heading or a caption cannot move the reading. The widest
extent of any content span is reported against the A4 text column
(20mm side margins), and every span outside it is listed, so a code line
that runs off the page is caught and named.

Used by tests/test_pdf_type_scale.py, and runnable on any PDF:

    python3 tests/pdf_type_scale.py file.pdf
"""

from __future__ import annotations

import json
import re
import sys
import unicodedata
from collections import Counter

MM = 72 / 25.4
MONO = re.compile(r"courier|mono|consol", re.I)


def measure(pdf_path: str) -> dict:
    import pymupdf as fitz

    doc = fitz.open(pdf_path)
    sizes = {"body": Counter(), "code": Counter(), "footer": Counter(), "header": Counter()}
    left, right = float("inf"), 0.0
    page_w = None
    outside = []
    for page in doc:
        page_w, page_h = page.rect.width, page.rect.height
        # Unclipped, so text laid out beyond the page edge is still seen.
        for block in page.get_text("dict", clip=fitz.INFINITE_RECT())["blocks"]:
            for line in block.get("lines", []):
                for span in line["spans"]:
                    text = span["text"].strip()
                    if not text:
                        continue
                    x0, y0, x1, y1 = span["bbox"]
                    size = round(span["size"], 1)
                    if y0 >= page_h - 25 * MM:
                        kind = "footer"
                    elif y1 <= 25 * MM:
                        kind = "header"
                    else:
                        kind = "code" if MONO.search(span["font"]) else "body"
                        left, right = min(left, x0), max(right, x1)
                        if x0 < 20 * MM - 0.5 or x1 > page_w - 20 * MM + 0.5:
                            outside.append({"page": page.number + 1, "x0": round(x0, 1),
                                            "x1": round(x1, 1), "font": span["font"],
                                            "size": size, "text": span["text"]})
                    sizes[kind][size] += len(text)
    out = {k: (c.most_common(1)[0][0] if c else None) for k, c in sizes.items()}
    out.update({
        "pages": len(doc),
        "content_left_pt": round(left, 1),
        "content_right_pt": round(right, 1),
        "column_left_pt": round(20 * MM, 1),
        "column_right_pt": round(page_w - 20 * MM, 1) if page_w else None,
        "outside_column": outside,
        "histogram": {k: dict(c.most_common(5)) for k, c in sizes.items()},
    })
    return out


def normalise(text: str) -> str:
    """Text with every space, line break, soft hyphen and zero-width
    character removed and ligatures expanded, so a cell that wrapped over
    lines compares equal to its source."""
    text = unicodedata.normalize("NFKC", text)
    return re.sub(r"[\s\u00ad\u200b\u2060]+", "", text)


def pdf_text(pdf_path: str) -> str:
    """The whole text layer of the PDF, normalised."""
    import pymupdf as fitz

    doc = fitz.open(pdf_path)
    return normalise("".join(page.get_text("text", clip=fitz.INFINITE_RECT()) for page in doc))


if __name__ == "__main__":
    for path in sys.argv[1:]:
        print(path, json.dumps(measure(path), sort_keys=True))
