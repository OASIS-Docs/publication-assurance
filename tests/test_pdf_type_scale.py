"""The PDF prints the OASIS print type scale: body 10pt, code 9pt, footer 8pt.

The OASIS Markdown stylesheet sets screen sizes only (12pt body and tables,
18pt h1, 10pt code), so a PDF's type size was whatever the renderer made of
them. wkhtmltopdf's smart shrinking scaled each document by its own content
width: NIEM NDR v6.0 PS01 printed an 8pt body and 6pt code. Headless Chrome
printed DMLex at 12pt. The PDF preprocessor now sets the scale in points under
@media print, and the renderer passes `--disable-smart-shrinking --dpi 288` so
wkhtmltopdf prints those points at their size.

The render test runs the real step 2 script, with the wkhtmltopdf build the
step 2 workflow installs, on a copy of the CSAF v2.1 csd01 package (249 pages
in its published form), and measures the PDF's text layer with PyMuPDF. The
CI job `pdf-render` installs both and sets REQUIRE_WKHTMLTOPDF=1, so there the
test cannot skip. The package's link to the published stylesheet is pointed at
.github/src/style.css, which differs from markdown-styles-v1.7.3.css only in
whitespace, so the test does not depend on docs.oasis-open.org.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys

import pytest

from conftest import CORPUS, REPO_ROOT
from pdf_type_scale import measure

SOURCE = (REPO_ROOT / ".github/src/pipeline/pdf_preprocessor.py").read_text()
SCRIPT = REPO_ROOT / ".github/scripts/step_2_convert_html_to_pdf_V2_0.sh"
REQUIRED = os.environ.get("REQUIRE_WKHTMLTOPDF") == "1"

SCALE = {
    "body": "10pt", "table": "9pt", "h1": "16pt", "h2": "14pt", "h3": "12pt",
    "h4": "11pt", "h5, h6": "10pt", "code": "9pt",
    "table code, td code, th code": "8.5pt",
}


def print_rules():
    """Every rule inside an @media print block of the injected stylesheet,
    as {selector: declarations}."""
    rules = {}
    for block in re.finditer(r"@media print\s*\{((?:[^{}]*\{[^{}]*\})*)\s*\}", SOURCE):
        for sel, decl in re.findall(r"([^{}]+?)\s*\{([^{}]*)\}", block.group(1)):
            sel = " ".join(re.sub(r"/\*.*?\*/", "", sel, flags=re.S).split())
            rules[sel] = decl
    return rules


def test_the_pdf_stylesheet_sets_the_print_type_scale():
    rules = print_rules()
    for selector, size in SCALE.items():
        assert selector in rules, f"no @media print rule for {selector!r}"
        assert re.search(rf"font-size:\s*{re.escape(size)}\s*!important", rules[selector]), \
            f"{selector} does not print at {size}: {rules[selector]!r}"
    assert "word-wrap: break-word" in rules["code"], rules["code"]
    blocks = next(s for s in rules if s.startswith("pre, .sourceCode"))
    assert re.search(r"font-size:\s*9pt\s*!important", rules[blocks]), rules[blocks]


def test_headings_stay_with_what_follows():
    rules = print_rules()
    sel = "h1, h2, h3, h4, h5, h6, h1big"
    assert sel in rules and "page-break-after: avoid" in rules[sel], rules.get(sel)


def test_the_render_job_installs_the_workflow_s_wkhtmltopdf():
    """The render test certifies one build. It must be the build that makes
    the PDFs."""
    deb = re.compile(r"https://github\.com/wkhtmltopdf/packaging/\S+\.deb")
    ci = deb.findall((REPO_ROOT / ".github/workflows/ci.yml").read_text())
    step2 = deb.findall((REPO_ROOT / ".github/workflows/"
                         "step_2_convert_md_to_html_pdf_final.yml").read_text())
    assert step2 and set(ci) == set(step2), (ci, step2)


def _have_renderer():
    try:
        import fitz  # noqa: F401
        import bs4  # noqa: F401
    except ImportError:
        return False
    return shutil.which("wkhtmltopdf") is not None


@pytest.mark.skipif(not REQUIRED and not _have_renderer(),
                    reason="needs wkhtmltopdf, PyMuPDF and bs4; the pdf-render CI job has them")
def test_a_real_package_prints_the_type_scale(tmp_path):
    pkg = tmp_path / "csaf/v2.1/csd01"
    shutil.copytree(CORPUS / "csaf/v2.1/csd01", pkg)
    (pkg / "csaf-v2.1-csd01.pdf").unlink()
    html = pkg / "csaf-v2.1-csd01.html"
    text = html.read_text(encoding="utf-8")
    link = "https://docs.oasis-open.org/styles/markdown-styles-v1.7.3.css"
    assert text.count(link) == 1
    shutil.copy(REPO_ROOT / ".github/src/style.css", pkg / ".style.css")
    html.write_text(text.replace(link, ".style.css"), encoding="utf-8")

    r = subprocess.run(["bash", str(SCRIPT), str(pkg)], capture_output=True, text=True,
                       env={**os.environ, "PYTHON": sys.executable}, cwd=tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    m = measure(str(pkg / "csaf-v2.1-csd01.pdf"))
    print("measured:", m)

    assert m["pages"] > 100, m["pages"]
    assert m["body"] == 10.0, m["histogram"]["body"]
    assert m["code"] == 9.0, m["histogram"]["code"]
    assert m["footer"] == 8.0, m["histogram"]["footer"]
    assert m["outside_column"] == [], m["outside_column"]
