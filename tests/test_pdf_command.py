"""The wkhtmltopdf command the pipeline builds, asserted token for token.

`build_command` carried a literal running header, 'Common Security Advisory
Framework Version 2.1', and a literal copyright year of 2025. Every PDF this
pipeline rendered for any TC therefore came out with the CSAF title across the
top of every page. Nothing in the repository exercised the pipeline, so nothing
could have caught it.

These tests pin the two values to the document being rendered.

Then (proposal 012, Sep 2026) the footer itself was wrong for every TC: the
file name with ".html", the render's date where a published OASIS PDF prints
the document's, no "Standards Track Work Product" line, and the title as a
running header on every page, the cover included. Published CSAF PDFs print
`csaf-v2.0-csd02 | Copyright (c) OASIS Open 2022. All Rights Reserved. /
Standards Track Work Product | 30 March 2022 - Page 2 of 122` and no header.
The footer is now an HTML footer built from the document.
"""

from __future__ import annotations

import importlib.util
import sys
import types

import pytest

from conftest import REPO_ROOT

bs4 = pytest.importorskip("bs4", reason="the rendering pipeline requires bs4")

PIPELINE = REPO_ROOT / ".github" / "src"


def _renderer_class():
    """Load pipeline.pdf_renderer by path.

    `.github/src` is not importable, and the package's own `__init__` pulls in
    every stage (and `requests` with them), so a stand-in package is registered
    that carries only the path relative imports need.
    """
    if "pipeline" not in sys.modules:
        pkg = types.ModuleType("pipeline")
        pkg.__path__ = [str(PIPELINE / "pipeline")]
        sys.modules["pipeline"] = pkg
    spec = importlib.util.spec_from_file_location(
        "pipeline.pdf_renderer", PIPELINE / "pipeline" / "pdf_renderer.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["pipeline.pdf_renderer"] = module
    spec.loader.exec_module(module)
    return module.PdfRenderer


PdfRenderer = _renderer_class()

PAGE = """<!DOCTYPE html><html><head><title>{title}</title></head>
<body><h1>{h1}</h1><h2>Committee Specification Draft 01</h2><h2>12 June {year}</h2>
<p>Copyright &copy; OASIS Open {year}. All Rights Reserved.</p>
</body></html>"""


def _render(tmp_path, html):
    src = tmp_path / "spec.html"
    src.write_text(html, encoding="utf-8")
    return PdfRenderer(str(src), str(tmp_path / "spec.pdf"))


def _flag(cmd, name):
    return cmd[cmd.index(name) + 1]


def test_there_is_no_running_header(tmp_path):
    """A published OASIS PDF has none, and a title there repeats on the cover."""
    r = _render(tmp_path, PAGE.format(title="Virtio Version 1.4",
                                      h1="Virtio Version 1.4", year="2026"))
    cmd = r.build_command(str(tmp_path / "spec.html"))
    assert not [t for t in cmd if t.startswith("--header")], cmd
    assert "Common Security Advisory Framework" not in " ".join(cmd)


def test_the_footer_is_the_published_one_read_from_the_document(tmp_path):
    src = tmp_path / "virtio-v1.4-csd01.html"
    src.write_text(PAGE.format(title="T", h1="T", year="2024"), encoding="utf-8")
    r = PdfRenderer(str(src), str(tmp_path / "spec.pdf"))
    cmd = r.build_command(str(src))
    assert _flag(cmd, "--footer-html").endswith(".html")
    footer = r.footer_html()
    for part in ("virtio-v1.4-csd01<", "Copyright © OASIS Open 2024. All Rights Reserved.",
                 "Standards Track Work Product", "12 June 2024 - Page", 'class="page"', 'class="topage"'):
        assert part in footer, part
    assert "virtio-v1.4-csd01.html" not in footer


def test_a_committee_note_is_non_standards_track(tmp_path):
    src = tmp_path / "widget-v1.0-cnd02.html"
    src.write_text(PAGE.format(title="T", h1="T", year="2026"), encoding="utf-8")
    assert "Non-Standards Track Work Product" in PdfRenderer(str(src), str(tmp_path / "w.pdf")).footer_html()


def test_a_document_without_a_date_line_prints_no_render_date(tmp_path):
    src = tmp_path / "x-v1.0-csd01.html"
    src.write_text("<html><body><h1>X</h1></body></html>", encoding="utf-8")
    footer = PdfRenderer(str(src), str(tmp_path / "x.pdf")).footer_html()
    assert "[date]" not in footer and ">Page <span" in footer


def test_a_document_with_no_title_element_falls_back_to_its_heading(tmp_path):
    src = tmp_path / "spec.html"
    src.write_text("<html><body><h1>DPS Version 1.0</h1></body></html>",
                   encoding="utf-8")
    r = PdfRenderer(str(src), str(tmp_path / "spec.pdf"))
    assert r.document_title() == "DPS Version 1.0"


def test_a_document_with_neither_gets_an_empty_header_not_another_tc_s_title(tmp_path):
    src = tmp_path / "spec.html"
    src.write_text("<html><body><p>text</p></body></html>", encoding="utf-8")
    r = PdfRenderer(str(src), str(tmp_path / "spec.pdf"))
    assert r.document_title() == ""


def test_the_documented_command_matches_the_built_one(tmp_path):
    """TRANSFORMS.md prints this command for a TC to run by hand. Every flag it
    prints must be one the pipeline actually passes, in the same order."""
    documented = [
        "--page-size", "A4", "--orientation", "Portrait",
        "--margin-top", "25mm", "--margin-right", "20mm",
        "--margin-bottom", "25mm", "--margin-left", "20mm",
        "--footer-html", "--footer-spacing", "4",
        "--no-outline", "--print-media-type",
        "--disable-smart-shrinking", "--dpi", "288",
        "--enable-local-file-access",
        "--load-error-handling", "ignore",
        "--load-media-error-handling", "ignore",
    ]
    transforms = (REPO_ROOT / "TRANSFORMS.md").read_text(encoding="utf-8")
    block = transforms.split("wkhtmltopdf \\", 1)[1].split("```", 1)[0]
    cmd = _render(tmp_path, PAGE.format(title="T", h1="T", year="2026")) \
        .build_command(str(tmp_path / "spec.html"))
    for token in documented:
        assert token in cmd, f"{token} is not in the command the pipeline builds"
        assert token in block, f"{token} is missing from TRANSFORMS.md"


def test_wkhtmltopdf_prints_css_points_at_their_size(tmp_path):
    """Smart shrinking scaled NIEM NDR v6.0's 12pt body to 8pt, and at 96 dpi
    a 10pt font rounds to 9.75pt. tests/test_pdf_type_scale.py measures the
    result of these two flags on the real build."""
    cmd = _render(tmp_path, PAGE.format(title="T", h1="T", year="2026")) \
        .build_command(str(tmp_path / "spec.html"))
    i = cmd.index("--print-media-type")
    assert cmd[i + 1:i + 4] == ["--disable-smart-shrinking", "--dpi", "288"], cmd


@pytest.mark.parametrize("name", ["foo-v1.0-cn01-part1-intro", "foo-v1.0-cnd01-part2-x", "foo-v1.0-cn01-errata01",
                                  "foo-v1.0-CN01", "foo-v1.0-cnprd02", "foo-v1.0-pnd01"])
def test_a_committee_or_project_note_in_any_file_name_shape_is_non_standards_track(tmp_path, name):
    src = tmp_path / f"{name}.html"
    src.write_text(PAGE.format(title="T", h1="T", year="2026"), encoding="utf-8")
    assert "Non-Standards Track Work Product" in PdfRenderer(str(src), str(tmp_path / "x.pdf")).footer_html()


@pytest.mark.parametrize("name", ["foo-v1.0-csd01-part1-intro", "foo-v1.0-os", "foo-v1.0-cs02-errata01"])
def test_a_specification_in_any_file_name_shape_is_standards_track(tmp_path, name):
    src = tmp_path / f"{name}.html"
    src.write_text(PAGE.format(title="T", h1="T", year="2026"), encoding="utf-8")
    footer = PdfRenderer(str(src), str(tmp_path / "x.pdf")).footer_html()
    assert "Standards Track Work Product" in footer and "Non-Standards" not in footer


def test_the_date_is_the_cover_s_not_an_earlier_one_in_the_text(tmp_path):
    src = tmp_path / "x-v1.0-csd01.html"
    src.write_text("<html><body><p>Drafted <span>1 May 2026</span></p><h1>X</h1>"
                   "<h2>Committee Specification Draft 01</h2><h2>12 June 2026</h2>"
                   "<table><tr><td>3 March 2021</td></tr></table></body></html>", encoding="utf-8")
    assert PdfRenderer(str(src), str(tmp_path / "x.pdf")).document_date() == "12 June 2026"


@pytest.mark.parametrize("notice,expected", [
    ("Copyright &copy; OASIS Open 2021-2026. All Rights Reserved.", "2021-2026"),
    ("Copyright &#169; OASIS Open 2024. All Rights Reserved.", "2024"),
    ("Copyright © 2023 OASIS Open. All Rights Reserved.", "2023"),
])
def test_the_copyright_year_is_the_document_s_in_any_form(tmp_path, notice, expected):
    src = tmp_path / "x-v1.0-csd01.html"
    src.write_text(f"<html><body><p>{notice}</p></body></html>", encoding="utf-8")
    assert PdfRenderer(str(src), str(tmp_path / "x.pdf")).copyright_line() == \
        f"Copyright © OASIS Open {expected}. All Rights Reserved."


def test_a_windows_1252_page_keeps_its_copyright_year(tmp_path):
    src = tmp_path / "x-v1.0-cn01.html"
    src.write_bytes('<html><head><meta charset="windows-1252"></head><body><p>Copyright \xa9 OASIS Open 2020. '
                    'All Rights Reserved.</p></body></html>'.encode("cp1252"))
    assert PdfRenderer(str(src), str(tmp_path / "x.pdf")).copyright_line() == \
        "Copyright © OASIS Open 2020. All Rights Reserved."


def test_numbers_that_do_not_settle_are_not_shipped(tmp_path, monkeypatch):
    """After four passes that keep moving, or a failure after a numbered
    print, the PDF is printed from the unnumbered HTML again."""
    src = tmp_path / "x-v1.0-csd01.html"
    src.write_text('<html><head></head><body><h1 id="table-of-contents">Table of Contents</h1>'
                   '<ul><li><a href="#a">1 A</a></li></ul><h1 id="a">1 A</h1></body></html>', encoding="utf-8")
    r = PdfRenderer(str(src), str(tmp_path / "x.pdf"))
    printed = []
    monkeypatch.setattr(r, "_convert_to_pdf", lambda path: printed.append(path))
    toc = sys.modules.get("pipeline.toc_pages") or importlib.import_module("pipeline.toc_pages")
    monkeypatch.setattr(toc, "main", lambda s, p, o: 1)
    r._number_contents()
    assert len(printed) == 5 and printed[-1] == str(src), printed
    calls = iter([1, LookupError("gone")])

    def flaky(s, p, o):
        v = next(calls)
        if isinstance(v, Exception):
            raise v
        return v
    printed.clear()
    monkeypatch.setattr(toc, "main", flaky)
    r._number_contents()
    assert printed[-1] == str(src), printed
