# Copyright 2026 OASIS Open
# SPDX-License-Identifier: Apache-2.0
# Authored by Michael Coletta, Technical Advisor to OASIS Open.
"""pdf-toc-pages: a PDF's contents give each entry's page, and the right one.

The first render of the DMLex v1.0 OS Markdown edition (Sep 2026) printed a
contents list with no page numbers where the published standard numbered
every entry; no check noticed. The CSAF v2.1 csd01 corpus PDF has the same
gap. The CSAF-CVRF v1.2 cs01 PDF (from Word) numbers its entries correctly.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys

import pytest

from conftest import CORPUS, REPO_ROOT, oasis_pub_check

sys.path.insert(0, str(REPO_ROOT / "pub-check"))
import validation_report  # noqa: E402

needs_poppler = pytest.mark.skipif(not (shutil.which("pdftotext") and shutil.which("pdfinfo")),
                                   reason="poppler (pdftotext, pdfinfo) is not installed")


def warnings(pdf):
    f = oasis_pub_check.Findings()
    oasis_pub_check.check_pdf_toc_pages(str(pdf), f)
    return [x["message"] for x in f.items if x["check"] == "pdf-toc-pages"]


def printed(tmp_path, numbers):
    """A contents page and eight sections, one per page, printed by Chrome.
    numbers: the page number to print against each entry, or None."""
    chrome = validation_report.find_browser()
    if not chrome:
        if os.environ.get("REQUIRE_CHROME") == "1":
            pytest.fail("REQUIRE_CHROME=1 but no Chrome or Chromium was found")
        pytest.skip("no Chrome or Chromium")
    rows = "".join(f"<p>{k} Section {k}{'&nbsp;' * 6 + str(n) if n else ''}</p>"
                   for k, n in enumerate(numbers, 1))
    body = "".join(f'<h1 style="break-before: page">{k} Section {k}</h1><p>Text {k}.</p>'
                   for k in range(1, len(numbers) + 1))
    src = tmp_path / "doc.html"
    src.write_text(f"<html><body><h1>Table of Contents</h1><pre style='font:inherit'>"
                   f"{rows.replace('<p>', '').replace('</p>', chr(10))}</pre>{body}</body></html>", encoding="utf-8")
    pdf = tmp_path / "doc.pdf"
    subprocess.run([chrome, "--headless", "--disable-gpu", "--no-sandbox", "--no-pdf-header-footer",
                    f"--print-to-pdf={pdf}", src.as_uri()], capture_output=True, timeout=120)
    assert pdf.is_file() and pdf.stat().st_size > 1000
    return pdf


@needs_poppler
def test_a_contents_without_page_numbers_warns(tmp_path):
    got = warnings(printed(tmp_path, [None] * 8))
    assert len(got) == 1 and "no page number for 8 of its 8 entries" in got[0]


@needs_poppler
def test_correct_page_numbers_pass(tmp_path):
    assert warnings(printed(tmp_path, [2, 3, 4, 5, 6, 7, 8, 9])) == []


@needs_poppler
def test_page_numbers_that_point_elsewhere_warn(tmp_path):
    got = warnings(printed(tmp_path, [9, 8, 7, 6, 5, 4, 3, 2]))
    assert len(got) == 1 and "at a page the heading is not on" in got[0]


@needs_poppler
def test_the_markdown_pipeline_corpus_pdf_warns_and_the_word_one_does_not():
    csaf = next((CORPUS / "csaf/v2.1/csd01").glob("csaf-v2.1-csd01.pdf"))
    got = warnings(csaf)
    assert len(got) == 1 and "no page number" in got[0]
    cvrf = next((CORPUS / "csaf-cvrf/v1.2/cs01").glob("*-cs01.pdf"))
    assert warnings(cvrf) == []


def test_a_bare_appendix_letter_is_a_contents_entry():
    """FOP prints DMLex's appendices in the contents as "A Informative material
    ... 126", with no "Appendix"; they were not read as entries (Sep 2026)."""
    E = oasis_pub_check._TOC_ENTRY
    for line in ("A Informative material on serializations (Informative) ........ 126",
                 "Appendix B References ........ 185", "A.2.2.1 NVH node: entry ........ 172"):
        assert E.match(line), line
    for line in ("A lexicographic resource contains entries.", "a. Conformant widgets"):
        assert not E.match(line), line


def test_invisible_characters_before_the_page_number_are_not_read_as_text(monkeypatch):
    """Typst prints U+2060 WORD JOINER before each contents page number, so
    the number did not stand alone after the leader and all 59 entries of
    CSAF v2.1 csd03 (Sep 2026) read as unnumbered. pdftotext's output is
    served by a stub here: the characters are the fixture."""
    titles = [f"{k}. Section {k}" for k in range(1, 7)]
    marks = ["⁠", "​", "﻿", "⁠", " ", "⁠"]
    toc = "Table of Contents\n" + "".join(
        f"{t}{' ' * 30}{mark}{k + 1}\n" for k, (t, mark) in enumerate(zip(titles, marks), 1))
    pages = {1: toc} | {k + 1: f"{t}\nBody text {k}.\n" for k, t in enumerate(titles, 1)}

    def run(cmd, **kw):
        class R:
            stdout = ""
        if cmd[0] == "pdfinfo":
            R.stdout = f"Pages:          {len(pages)}\n"
        elif "-f" in cmd:
            R.stdout = pages[int(cmd[cmd.index("-f") + 1])]
        else:
            R.stdout = "\f".join(pages[n] for n in sorted(pages))
        return R

    monkeypatch.setattr(oasis_pub_check.shutil, "which", lambda name: name)
    monkeypatch.setattr(oasis_pub_check.subprocess, "run", run)
    f = oasis_pub_check.Findings()
    oasis_pub_check.check_pdf_toc_pages("typst.pdf", f)
    assert [x["message"] for x in f.items if x["check"] == "pdf-toc-pages"] == []
    assert f.observed["pdf-toc-pages"]["with_page_numbers"] == "6"
    assert f.observed["pdf-toc-pages"]["wrong"] == "0"
