"""The wkhtmltopdf command the pipeline builds, asserted token for token.

`build_command` carried a literal running header, 'Common Security Advisory
Framework Version 2.1', and a literal copyright year of 2025. Every PDF this
pipeline rendered for any TC therefore came out with the CSAF title across the
top of every page. Nothing in the repository exercised the pipeline, so nothing
could have caught it.

These tests pin the two values to the document being rendered.
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
<body><h1>{h1}</h1><p>Copyright &copy; OASIS Open {year}. All Rights Reserved.</p>
</body></html>"""


def _render(tmp_path, html):
    src = tmp_path / "spec.html"
    src.write_text(html, encoding="utf-8")
    return PdfRenderer(str(src), str(tmp_path / "spec.pdf"))


def _flag(cmd, name):
    return cmd[cmd.index(name) + 1]


def test_the_running_header_is_this_document_s_title(tmp_path):
    r = _render(tmp_path, PAGE.format(title="Virtio Version 1.4",
                                      h1="Virtio Version 1.4", year="2026"))
    cmd = r.build_command(str(tmp_path / "spec.html"))
    assert _flag(cmd, "--header-center") == "Virtio Version 1.4"
    assert "Common Security Advisory Framework" not in " ".join(cmd)


def test_the_footer_year_is_the_document_s_own(tmp_path):
    r = _render(tmp_path, PAGE.format(title="T", h1="T", year="2024"))
    cmd = r.build_command(str(tmp_path / "spec.html"))
    assert _flag(cmd, "--footer-center") == \
        "Copyright © OASIS Open 2024. All Rights Reserved."


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
        "--header-spacing", "6", "--header-font-size", "10",
        "--header-center", "--footer-line", "--footer-spacing", "4",
        "--footer-left", "--footer-center", "--footer-right",
        "--footer-font-size", "8", "--footer-font-name", "Times",
        "--no-outline", "--print-media-type", "--enable-local-file-access",
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
