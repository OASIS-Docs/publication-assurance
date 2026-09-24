"""A figure wider than the printable page must not reach the PDF unnoticed.

DMLex v1.0 (Sep 2026): the Markdown edition's 49 figures carried no width, so
each rendered at its natural size. The UML diagram is 1505pt wide on a 643px
line, and Appendix D ran off the page. The text verifier and the gate had no
check that could see it; an agent found it by reading screenshots.

Two defences, pinned here with the real DMLex figures:

- the pipeline's PDF stylesheet caps images at the line width, so the next
  package whose figures carry no width still prints inside the margins;
- `image-policy` warns on an <img> whose effective width exceeds the
  printable width when the package's own CSS sets no max-width, because the
  PDF then depends on whichever renderer prints it.
"""

from __future__ import annotations

import re
import shutil

from conftest import FIXTURES, REPO_ROOT, oasis_pub_check

FIG = FIXTURES / "image_width"
SOURCE = (REPO_ROOT / ".github/src/pipeline/pdf_preprocessor.py").read_text()


def stage(tmp_path, body, css=None):
    for name in ("dmlex_uml.svg", "entry.svg", "OASISLogo-v3.0.png"):
        shutil.copy(FIG / name, tmp_path / name)
    head = f"<style>{css}</style>" if css else ""
    html = f"<html><head>{head}</head><body>{body}</body></html>"
    return str(tmp_path), html


def wide(tmp_path, body, css=None):
    stage_dir, html = stage(tmp_path, body, css)
    f = oasis_pub_check.Findings()
    oasis_pub_check.check_image_policy(stage_dir, html, f)
    return [x for x in f.items if "wider than the printable" in x["message"]]


def test_pdf_stylesheet_caps_images_at_the_line_width():
    m = re.search(r"(?m)^\s*img\s*\{(.*?)\}", SOURCE, re.S)
    assert m, "the PDF preprocessor stylesheet has no img rule"
    assert "max-width: 100%" in m.group(1), m.group(1)
    assert "height: auto" in m.group(1), m.group(1)


def test_the_dmlex_uml_diagram_at_natural_size_is_flagged(tmp_path):
    hits = wide(tmp_path, '<img alt="" src="dmlex_uml.svg"/>')
    assert len(hits) == 1, hits
    assert "dmlex_uml.svg" in hits[0]["message"] and "2007px" in hits[0]["message"], hits


def test_a_881px_diagram_without_a_width_is_flagged(tmp_path):
    assert len(wide(tmp_path, '<img src="entry.svg">')) == 1


def test_the_fixed_dmlex_markup_is_silent(tmp_path):
    body = ('<img alt="" src="dmlex_uml.svg" width="567"/>'
            '<img alt="" src="entry.svg" width="567"/>'
            '<img alt="OASIS Logo" src="OASISLogo-v3.0.png"/>')
    assert wide(tmp_path, body) == []


def test_a_percentage_width_is_silent(tmp_path):
    assert wide(tmp_path, '<img src="dmlex_uml.svg" style="width: 100%">') == []


def test_a_package_max_width_rule_is_silent(tmp_path):
    css = "img { max-width: 100%; height: auto; }"
    assert wide(tmp_path, '<img src="dmlex_uml.svg">', css) == []


def test_an_explicit_width_wider_than_the_page_is_flagged(tmp_path):
    assert len(wide(tmp_path, '<img src="entry.svg" width="900">')) == 1


def test_it_is_a_warning_not_a_blocker(tmp_path):
    hits = wide(tmp_path, '<img src="dmlex_uml.svg">')
    assert hits and all(x["severity"] == oasis_pub_check.WARN for x in hits), hits
