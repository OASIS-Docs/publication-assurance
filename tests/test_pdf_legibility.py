"""The PDF's body text must print near the size the stylesheet declares.

DMLex v1.0 (Sep 2026): one unwrappable inline path widened the page and Chrome
scaled every page to fit, so the stylesheet's 12pt body printed at about 8pt
across 140 pages. The gate checked the PDF's text and fonts and could not see
it. `pdf-legibility` compares the document-wide median word height
(`pdftotext -bbox`) with the body size the package declares, and warns below
85%. A word box runs about 1.05 to 1.15 times the type size, so the reading is
generous: it fires on shrinkage, not on a font's proportions.

Fixtures are eight pages of the real DMLex render from v1.4.1 (the shrunk
one) and eleven pages of the v1.4.2 render (the fixed one), cut with qpdf.
The CSAF corpus supplies the rest: v2.1 csd01 prints at full size, the v2.0
editions were printed by wkhtmltopdf 0.12.5 at about 7pt, and the CVRF v1.2
editions came from Word, which the check does not judge.
"""

from __future__ import annotations

import shutil

import pytest

from conftest import CORPUS, FIXTURES, oasis_pub_check

pytestmark = pytest.mark.skipif(not shutil.which("pdftotext"),
                                reason="pdftotext (poppler) is the check's instrument")

FIX = FIXTURES / "pdf_legibility"
SHRUNK = FIX / "dmlex-v1.0-os-v1.4.1-render-p30-37.pdf"
FIXED = FIX / "dmlex-v1.0-os-v1.4.2-render-p48-58.pdf"
V173 = ('<link href="https://docs.oasis-open.org/styles/markdown-styles-v1.7.3.css" '
        'rel="stylesheet"/>')


def run(pdf, html, stage_dir=None):
    f = oasis_pub_check.Findings()
    oasis_pub_check.check_pdf_legibility(str(pdf), str(stage_dir or FIX), html, f)
    return f


def warns(f):
    return [x for x in f.items if x["check"] == "pdf-legibility" and x["severity"] == "WARN"]


def html_of(stage):
    return next(stage.glob("*.html")).read_text(encoding="utf-8", errors="replace")


def test_the_shrunk_dmlex_render_is_flagged():
    w = warns(run(SHRUNK, f"<html><head>{V173}</head></html>"))
    assert len(w) == 1, w
    assert "8.9pt" in w[0]["message"] and "12pt" in w[0]["message"], w


def test_the_fixed_dmlex_render_is_silent():
    f = run(FIXED, f"<html><head>{V173}</head></html>")
    assert warns(f) == []
    assert f.observed["pdf-legibility"]["median_word_height_pt"] == "13.4"


def test_the_package_own_css_is_the_authority():
    """A package that declares a 9pt body is not shrunk at 8.9pt."""
    html = f"<html><head>{V173}<style>body {{ font-size: 9pt; }}</style></head></html>"
    assert warns(run(SHRUNK, html)) == []


def test_a_px_body_size_is_converted():
    """markdown-styles v1.7.1 and earlier declare 15px, which is 11.25pt."""
    html = ('<link href="https://docs.oasis-open.org/templates/css/'
            'markdown-styles-v1.7.1.css" rel="stylesheet"/>')
    w = warns(run(SHRUNK, html))
    assert len(w) == 1 and "11.25pt" in w[0]["message"], w


def test_no_declared_size_is_skipped_with_info():
    f = run(SHRUNK, "<html><head></head></html>")
    assert warns(f) == []
    assert any(x["check"] == "pdf-legibility" and x["severity"] == "INFO" for x in f.items)


def test_csaf_v2_1_csd01_is_silent():
    stage = CORPUS / "csaf/v2.1/csd01"
    assert warns(run(stage / "csaf-v2.1-csd01.pdf", html_of(stage), stage)) == []


def test_csaf_v2_0_os_printed_small_is_flagged():
    """wkhtmltopdf 0.12.5 printed the v1.7.3a stylesheet's 12pt at about 7pt."""
    stage = CORPUS / "csaf/v2.0/os"
    w = warns(run(stage / "csaf-v2.0-os.pdf", html_of(stage), stage))
    assert len(w) == 1 and "7.8pt" in w[0]["message"], w


def test_a_word_built_pdf_is_not_judged_against_css():
    stage = CORPUS / "csaf-cvrf/v1.2/cs01"
    html = V173  # even with a stylesheet in reach, Word did not use it
    assert warns(run(stage / "csaf-cvrf-v1.2-cs01.pdf", html, stage)) == []


def test_a_landscape_pdf_is_skipped():
    pdf = CORPUS / "eox-core-v1.0-csd01/eox-core-v1.0-csd01-pub-check-validation-2026-07-27.pdf"
    assert warns(run(pdf, V173)) == []


def test_it_runs_on_a_package(tmp_path):
    """Wired into the gate's PDF suite, not only callable."""
    stage = tmp_path / "csaf/v2.0/os"
    shutil.copytree(CORPUS / "csaf/v2.0/os", stage)
    f = oasis_pub_check.Findings()
    oasis_pub_check.run(str(stage), f)
    assert any(x["check"] == "pdf-legibility" for x in f.items), \
        sorted({x["check"] for x in f.items})


# Counterexamples from the independent verification of this change.

def test_an_html_root_size_is_not_the_body_size():
    html = f"<html><head>{V173}<style>html {{ font-size: 10px; }}</style></head></html>"
    assert len(warns(run(SHRUNK, html))) == 1


def test_a_rem_body_is_resolved_against_the_root():
    html = (f"<html><head>{V173}<style>html {{ font-size: 10px; }} "
            f"body {{ font-size: 1.6rem; }}</style></head></html>")
    w = warns(run(SHRUNK, html))
    assert len(w) == 1 and "12pt" in w[0]["message"], w


def test_an_unlinked_css_file_in_the_tree_is_not_the_body_authority(tmp_path):
    (tmp_path / "docson" / "css").mkdir(parents=True)
    (tmp_path / "docson" / "css" / "docson.css").write_text("body { font-size: 10px; }")
    html = f"<html><head>{V173}<style>body {{ font-size: 12pt; }}</style></head></html>"
    assert len(warns(run(SHRUNK, html, tmp_path))) == 1


def test_font_shorthand_and_single_quoted_links_are_read():
    assert len(warns(run(SHRUNK, "<style>body { font: 12pt/1.4 Arial; }</style>"))) == 1
    single = ("<link href='https://docs.oasis-open.org/templates/css/"
              "markdown-styles-v1.7.3a.css' rel='stylesheet'>")
    assert len(warns(run(SHRUNK, single))) == 1


def test_a_landscape_cover_does_not_skip_a_portrait_body(tmp_path):
    import subprocess
    cover = CORPUS / "eox-core-v1.0-csd01/eox-core-v1.0-csd01-pub-check-validation-2026-07-27.pdf"
    out = tmp_path / "mixed.pdf"
    subprocess.run(["qpdf", "--empty", "--pages", str(cover), "1", str(SHRUNK), "--", str(out)],
                   check=True)
    assert len(warns(run(out, f"<html><head>{V173}</head></html>"))) == 1


def test_a_chrome_pdf_resaved_by_acrobat_is_still_judged():
    """Creator names the renderer; a re-save only changes the Producer."""
    f = oasis_pub_check.Findings()
    oasis_pub_check.check_pdf_legibility(
        str(SHRUNK), str(FIX), f"<html><head>{V173}</head></html>", f,
        _info="Creator:        HeadlessChrome/153\nProducer:       Adobe Acrobat Pro 2024\n")
    assert len(warns(f)) == 1


def test_a_word_creator_is_still_skipped():
    f = oasis_pub_check.Findings()
    oasis_pub_check.check_pdf_legibility(
        str(SHRUNK), str(FIX), f"<html><head>{V173}</head></html>", f,
        _info="Creator:        Microsoft Word 2016\nProducer:       Microsoft Word 2016\n")
    assert warns(f) == []


def test_an_unreadable_pdf_says_so(tmp_path):
    bad = tmp_path / "bad.pdf"
    bad.write_bytes(b"%PDF-1.4 not really")
    f = run(bad, f"<html><head>{V173}</head></html>", tmp_path)
    assert any(x["check"] == "pdf-legibility" for x in f.items), f.items
