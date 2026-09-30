# Copyright 2026 OASIS Open
# SPDX-License-Identifier: Apache-2.0
# Authored by Michael Coletta, Technical Advisor to OASIS Open.
"""A multi-line code block prints as ONE block (PdfPreprocessor's print CSS).

The OASIS Markdown stylesheet that step 1 links
(markdown-styles-v1.8.1-cn_final.css) sets `code,kbd,pre,samp {display:inline}`.
With the print styles' border, padding and box-decoration-break: clone, every
line of a <pre> printed in its own overlapping, clipped box: 447 of 667
multi-line blocks in the CSAF v2.1 CSD03 PDF, in Chrome and in wkhtmltopdf. A
pandoc-highlighted block also framed its <code> and its wrapping div (both
carry the `sourceCode` class the print styles frame) and printed frames inside
frames.

The printed check counts the background fills in the print styles' <pre>
colour (#f8f8f8) on the page Chrome prints from the preprocessed HTML: one per
line when broken, one per block when fixed. publisher-toolkit carried the same
rules as a local override (lib/robust_run.py PRINT_FIXES_CSS) until it
re-vendors this step.
"""

from __future__ import annotations

import importlib.util
import os
import re
import shutil
import subprocess
import sys
import types
import zlib

import pytest

from conftest import REPO_ROOT

pytest.importorskip("bs4", reason="the rendering pipeline requires bs4")

sys.path.insert(0, str(REPO_ROOT / "pub-check"))
import validation_report  # noqa: E402

PIPELINE = REPO_ROOT / ".github" / "src" / "pipeline"


def _preprocessor_class():
    """pipeline.pdf_preprocessor by path, under a stand-in package (the real
    package's __init__ imports every stage, and requests with them)."""
    if "pipeline" not in sys.modules:
        pkg = types.ModuleType("pipeline")
        pkg.__path__ = [str(PIPELINE)]
        sys.modules["pipeline"] = pkg
    spec = importlib.util.spec_from_file_location("pipeline.pdf_preprocessor",
                                                  PIPELINE / "pdf_preprocessor.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["pipeline.pdf_preprocessor"] = module
    spec.loader.exec_module(module)
    return module.PdfPreprocessor


PdfPreprocessor = _preprocessor_class()

# The house sheet's code rule, verbatim (markdown-styles-v1.8.1-cn_final.css).
HOUSE = """code,kbd,pre,samp {
    font-family:CourierNew, monospace;
    font-size:1em;
    white-space: pre-wrap;
    background-color:#e8e8e8;
    display:inline;
}"""

# pandoc's highlighting styles, as it writes them into a standalone page.
PANDOC = """pre > code.sourceCode { white-space: pre; position: relative; }
pre > code.sourceCode > span { line-height: 1.25; }
.sourceCode { overflow: visible; }
code.sourceCode > span { color: inherit; text-decoration: inherit; }
div.sourceCode { margin: 1em 0; }
pre.sourceCode { margin: 0; }"""

PLAIN = """<pre><code>{
  "first": "line one",
  "second": "line two"
}</code></pre>"""

HIGHLIGHTED = """<div class="sourceCode" id="cb1"><pre class="sourceCode json"><code class="sourceCode json"><span id="cb1-1"><a href="#cb1-1" aria-hidden="true" tabindex="-1"></a><span class="fu">{</span></span>
<span id="cb1-2"><a href="#cb1-2" aria-hidden="true" tabindex="-1"></a>  <span class="dt">&quot;first&quot;</span><span class="fu">:</span> <span class="st">&quot;line one&quot;</span></span>
<span id="cb1-3"><a href="#cb1-3" aria-hidden="true" tabindex="-1"></a><span class="fu">}</span></span></code></pre></div>"""


def page(block):
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>Code</title>
<style>{HOUSE}</style><style>{PANDOC}</style></head><body>
<h1>Code Version 1.0</h1><h2>12 June 2026</h2>
<p>Use the <code>inline_name</code> here.</p>
{block}
<p>After the block.</p></body></html>"""


def preprocess(tmp_path, block):
    src = tmp_path / "code-v1.0-csd01.html"
    src.write_text(page(block), encoding="utf-8")
    out = tmp_path / ".code-v1.0-csd01-pdf.html"
    PdfPreprocessor(src, out).preprocess()
    return out


def test_the_code_block_rules_come_after_the_house_sheet(tmp_path):
    head = preprocess(tmp_path, PLAIN).read_text(encoding="utf-8").split("</head>", 1)[0]
    fix = head.find("pre { display: block !important; }")
    assert fix != -1, "the preprocessed HTML does not make a <pre> a block"
    assert fix > head.find("display:inline") > -1, "the fix must follow the house sheet it overrides"
    for rule in ("pre code, pre code[class] { border: none !important; padding: 0 !important; "
                 "background: none !important; }",
                 "div.sourceCode { border: none !important; padding: 0 !important; "
                 "background: none !important; }"):
        assert rule in head[fix:], rule


def chrome_pdf(html):
    chrome = validation_report.find_browser()
    if not chrome:
        if os.environ.get("REQUIRE_CHROME") == "1":
            pytest.fail("REQUIRE_CHROME=1 but no Chrome or Chromium was found")
        pytest.skip("no Chrome or Chromium")
    pdf = html.with_name("code-v1.0-csd01.pdf")
    subprocess.run([chrome, "--headless", "--disable-gpu", "--no-sandbox", "--no-pdf-header-footer",
                    f"--print-to-pdf={pdf}", html.as_uri()], capture_output=True, timeout=180)
    assert pdf.is_file()
    return pdf


PRE_BACKGROUND = (0.973, 0.973, 0.973)  # #f8f8f8
OP = re.compile(rb"(-?\d*\.?\d+)\s+(-?\d*\.?\d+)\s+(-?\d*\.?\d+)\s+(?:rg|sc|scn)\b|(?<![\w.])(f\*?)(?![\w*])")


def background_fills(pdf):
    """Filled shapes painted in the print styles' <pre> background, read from
    every Flate content stream of the PDF (a one-page print): standard
    library only, as the test job installs no PDF reader."""
    fills = 0
    for raw in re.findall(rb"stream\r?\n(.*?)\r?\nendstream", pdf.read_bytes(), re.S):
        try:
            ops = zlib.decompress(raw)
        except zlib.error:
            continue
        color = None
        for m in OP.finditer(ops):
            if m.group(4):
                fills += color == PRE_BACKGROUND
            else:
                color = tuple(round(float(x), 3) for x in m.group(1, 2, 3))
    return fills


@pytest.mark.parametrize("block", [PLAIN, HIGHLIGHTED], ids=["plain-pre", "pandoc-sourceCode"])
def test_a_multi_line_code_block_prints_as_one_block(tmp_path, block):
    pdf = chrome_pdf(preprocess(tmp_path, block))
    assert background_fills(pdf) == 1, "the code block did not print as one box"
    if shutil.which("pdftotext"):
        text = subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True, text=True,
                              timeout=60).stdout
        assert re.search(r"Use the inline_name here\.", text), "inline <code> no longer prints inline"
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        i = lines.index("{")
        assert lines[i + 1].startswith('"first": "line one"'), lines
