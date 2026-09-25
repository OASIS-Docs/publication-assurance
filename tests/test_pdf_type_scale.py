"""The PDF prints the OASIS print type scale: body 10pt, code 9pt, footer 8pt.

The OASIS Markdown stylesheet sets screen sizes only (12pt body and tables,
18pt h1, 10pt code), so a PDF's type size was whatever the renderer made of
them. wkhtmltopdf's smart shrinking scaled each document by its own content
width: NIEM NDR v6.0 PS01 printed an 8pt body and 6pt code. Headless Chrome
printed DMLex at 12pt. The PDF preprocessor now sets the scale in points under
@media print, and the renderer passes `--disable-smart-shrinking --dpi 288` so
wkhtmltopdf prints those points at their size.

The render test runs the real step 2 script, with the wkhtmltopdf build the
step 2 workflow installs, on copies of the CSAF v2.1 csd01 package (it renders
at 244 pages; the corpus copy of its PDF has 249) and the CSAF v2.0 OS package
(154 pages), and measures the PDF's text
layer with PyMuPDF. It also requires every table row of the HTML to be in the
PDF: with the print scale and no smart shrinking, the eight-column remediation
matrix was wider than the column and wkhtmltopdf dropped its last column, which
leaves no text anywhere for a position check to find. The
CI job `pdf-render` installs both and sets REQUIRE_WKHTMLTOPDF=1, so there the
test cannot skip. Each package's link to the published stylesheet is pointed
at .github/src/style.css, which differs from markdown-styles-v1.7.3.css and
v1.7.3a.css only in whitespace, so the test does not depend on
docs.oasis-open.org for its styles.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys

import pytest

from conftest import CORPUS, REPO_ROOT
from pdf_type_scale import measure, normalise, pdf_text

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
    sel = "h1, h2, h3, h4, h5, h6, h1big, .keep-with-next"
    assert sel in rules and "page-break-after: avoid" in rules[sel], rules.get(sel)


def _preprocessor():
    """Load pipeline.pdf_preprocessor by path, as test_pdf_command.py loads
    the renderer."""
    import importlib.util
    import types
    pytest.importorskip("bs4", reason="the preprocessor needs bs4, which CI installs")
    if "pipeline" not in sys.modules:
        pkg = types.ModuleType("pipeline")
        pkg.__path__ = [str(REPO_ROOT / ".github/src/pipeline")]
        sys.modules["pipeline"] = pkg
    spec = importlib.util.spec_from_file_location(
        "pipeline.pdf_preprocessor", REPO_ROOT / ".github/src/pipeline/pdf_preprocessor.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.PdfPreprocessor


CAPTIONS = """<html><head></head><body>
<p id="eg">Example 1:</p>
<pre><code>{ }</code></pre>
<p id="fig">Figure 2: the model</p>
<p><img src="model.png"/></p>
<p id="plain">Plain paragraph.</p>
<p id="next">Followed by text.</p>
<table><tr><th><code>no_fix_planned</code></th><td>allowed</td></tr></table>
</body></html>"""


def test_captions_are_kept_with_what_follows_in_the_preprocessed_html(tmp_path):
    """wkhtmltopdf has no :has(), so the preprocessor tags the paragraph."""
    from bs4 import BeautifulSoup
    src, out = tmp_path / "in.html", tmp_path / "out.html"
    src.write_text(CAPTIONS, encoding="utf-8")
    _preprocessor()(src, out).preprocess()
    soup = BeautifulSoup(out.read_text(encoding="utf-8"), "html.parser")
    kept = {p["id"] for p in soup.select("p.keep-with-next")}
    assert kept == {"eg", "fig"}, kept
    css = soup.find_all("style")[-1].string
    assert re.search(r"\.keep-with-next\s*\{[^}]*page-break-after:\s*avoid", css), css
    assert ":has(" not in re.sub(r"/\*.*?\*/", "", css, flags=re.S)


def test_code_in_a_table_cell_can_break_after_underscores(tmp_path):
    from bs4 import BeautifulSoup
    src, out = tmp_path / "in.html", tmp_path / "out.html"
    src.write_text(CAPTIONS, encoding="utf-8")
    _preprocessor()(src, out).preprocess()
    code = BeautifulSoup(out.read_text(encoding="utf-8"), "html.parser").select_one("th code")
    assert code.get_text() == "no_fix_planned"
    assert len(code.find_all("wbr")) == 2, code


def test_trailing_spaces_in_a_code_block_are_removed_and_words_are_not_joined(tmp_path):
    """Under pre-wrap, trailing spaces hang past the block's edge (CSAF v2.0
    OS, 'Supported digests'). A space before an inline element is not at a
    line end and stays."""
    from bs4 import BeautifulSoup
    src, out = tmp_path / "in.html", tmp_path / "out.html"
    src.write_text("<html><head></head><body><pre><code> -md4      \n -sha1   \n"
                   "a <b>b</b>   </code></pre></body></html>", encoding="utf-8")
    _preprocessor()(src, out).preprocess()
    pre = BeautifulSoup(out.read_text(encoding="utf-8"), "html.parser").pre
    assert pre.get_text() == " -md4\n -sha1\na b", repr(pre.get_text())


def test_the_pdf_copy_drops_base_href_and_keeps_its_links(tmp_path):
    """CSAF v2.0 OS carries <base href> to the live site, so its relative
    stylesheet and images were fetched from docs.oasis-open.org. The PDF copy
    drops it; the published HTML keeps it; a relative link is made absolute
    first, and a fragment link stays internal."""
    from bs4 import BeautifulSoup
    base = "https://docs.oasis-open.org/csaf/csaf/v2.0/os/csaf-v2.0-os.html"
    page = (f'<html><head><base href="{base}"/><link href="style.css" rel="stylesheet"/>'
            '</head><body><a id="f" href="#s1">s</a><a id="r" href="schemas/x.json">x</a>'
            '<a id="m" href="mailto:a@b.c">m</a><a id="p" href="//www.oasis-open.org/x">p</a>'
            '<img src="images/a.png"/></body></html>')
    src, out = tmp_path / "in.html", tmp_path / "out.html"
    src.write_text(page, encoding="utf-8")
    _preprocessor()(src, out).preprocess()
    soup = BeautifulSoup(out.read_text(encoding="utf-8"), "html.parser")
    assert soup.find("base") is None
    assert soup.find(id="f")["href"] == "#s1"
    assert soup.find(id="r")["href"] == \
        "https://docs.oasis-open.org/csaf/csaf/v2.0/os/schemas/x.json"
    assert soup.find(id="m")["href"] == "mailto:a@b.c"
    assert soup.find(id="p")["href"] == "https://www.oasis-open.org/x"
    assert soup.find("link")["href"] == "style.css" and soup.img["src"] == "images/a.png"
    assert "<base" in src.read_text(encoding="utf-8"), "the source HTML must keep its base"


def test_header_code_takes_the_header_colour():
    rule = print_rules()["th code"]
    assert "color: inherit" in rule and "background: transparent" in rule, rule


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


# (stage, stylesheet link in the package, rows the package's tables hold)
PACKAGES = {
    "csaf/v2.1/csd01": ("https://docs.oasis-open.org/styles/markdown-styles-v1.7.3.css", 100),
    "csaf/v2.0/os": ("https://docs.oasis-open.org/templates/css/markdown-styles-v1.7.3a.css", 50),
}


@pytest.mark.skipif(not REQUIRED and not _have_renderer(),
                    reason="needs wkhtmltopdf, PyMuPDF and bs4; the pdf-render CI job has them")
@pytest.mark.parametrize("stage", sorted(PACKAGES))
def test_a_real_package_prints_the_type_scale(tmp_path, stage):
    link, min_rows = PACKAGES[stage]
    name = "csaf-" + "-".join(stage.split("/")[1:])
    pkg = tmp_path / stage
    shutil.copytree(CORPUS / stage, pkg)
    for f in pkg.glob("*.pdf"):
        f.unlink()
    html = pkg / f"{name}.html"
    text = html.read_text(encoding="utf-8")
    rows = _table_rows(text)
    assert text.count(link) == 1
    shutil.copy(REPO_ROOT / ".github/src/style.css", pkg / ".style.css")
    text = text.replace(link, ".style.css")
    html.write_text(text, encoding="utf-8")

    r = subprocess.run(["bash", str(SCRIPT), str(pkg)], capture_output=True, text=True,
                       env={**os.environ, "PYTHON": sys.executable}, cwd=tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    m = measure(str(pkg / f"{name}.pdf"))
    print("measured:", stage, m)

    assert m["pages"] > 100, m["pages"]
    assert m["body"] == 10.0, m["histogram"]["body"]
    assert m["code"] == 9.0, m["histogram"]["code"]
    assert m["footer"] == 8.0, m["histogram"]["footer"]
    printed = pdf_text(str(pkg / f"{name}.pdf"))
    assert len(rows) > min_rows, len(rows)
    missing = [r for r in rows if normalise(r) not in printed]
    assert missing == [], f"{len(missing)} of {len(rows)} table rows are not in the PDF: {missing}"
    assert m["outside_column"] == [], m["outside_column"]


def _table_rows(html: str) -> list[str]:
    """Each table row's text, its cells in order. A row is printed left to
    right, so a row whose last cell was dropped no longer matches."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    rows = ["".join(c.get_text() for c in tr.find_all(["td", "th"]))
            for tr in soup.select("table tr")]
    return [r for r in rows if normalise(r)]
