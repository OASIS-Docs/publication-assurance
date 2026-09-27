# Copyright 2026 OASIS Open
# SPDX-License-Identifier: Apache-2.0
# Authored by Michael Coletta, Technical Advisor to OASIS Open.
"""toc_pages: the page each contents entry gives is the page its heading is
printed on (proposal 012).

Each case is printed by Chrome, whose PDF carries a named destination for
every heading, the truth. text_pages, the path a wkhtmltopdf PDF takes (it
has no named destinations), must find the same pages. The cases are the
adversarial review's counterexamples: a cross-reference to a heading
printed before it, duplicate titles, a contents heading that says only
"Contents", a contents list over several pages, links whose href is not
their first attribute, a section number outside the link, and a later list
of links that is not the contents (NIEM NDR v6.0 OS shape).
"""

from __future__ import annotations

import html as html_lib
import importlib.util
import os
import re
import subprocess
import sys

import pytest

from conftest import REPO_ROOT

sys.path.insert(0, str(REPO_ROOT / "pub-check"))
import validation_report  # noqa: E402

spec = importlib.util.spec_from_file_location("toc_pages", REPO_ROOT / ".github/src/pipeline/toc_pages.py")
T = importlib.util.module_from_spec(spec)
spec.loader.exec_module(T)

PB = '<div style="page-break-after:always"></div>'
H = '<h1 id="table-of-contents">Table of Contents</h1>'


def doc(toc, body, heading=H):
    return (f'<!DOCTYPE html><html><head><meta charset="utf-8"><title>T</title></head><body>'
            f'<h1>Spec</h1><p>12 June 2026</p>{PB}{heading}\n{toc}\n{PB}{body}</body></html>')


def sec(title, id_, prose="Body text."):
    return f'<h2 id="{id_}">{title}</h2><p>{prose}</p>{PB}'


def plain(n=6, a=lambda i: f'<a href="#s{i}">{i} Section {i}</a>'):
    return "<ul>" + "".join(f"<li>{a(i)}</li>" for i in range(1, n + 1)) + "</ul>"


CASES = {
    "xref_before": doc(plain(), sec("1 Section 1", "s1", "See section 5 Section 5 for details.")
                       + "".join(sec(f"{i} Section {i}", f"s{i}") for i in range(2, 7))),
    "dup_unnumbered": doc('<ul><li><a href="#a">Alpha</a><ul><li><a href="#a-ov">Overview</a></li></ul></li>'
                          '<li><a href="#b">Beta</a><ul><li><a href="#b-ov">Overview</a></li></ul></li></ul>',
                          sec("Alpha", "a") + sec("Overview", "a-ov")
                          + sec("Beta", "b", "Beta starts with an overview of the model.") + "<p>filler</p>" + PB
                          + sec("Overview", "b-ov")),
    "contents_word": doc(plain(), "".join(sec(f"{i} Section {i}", f"s{i}") for i in range(1, 7)),
                         heading='<h1 id="table-of-contents">Contents</h1>'),
    "long_toc": doc(plain(150, lambda i: f'<a href="#s{i}">{i} Topic {i}</a>'),
                    "".join(f'<h2 id="s{i}">{i} Topic {i}</h2><p>' + "Lorem ipsum dolor sit amet. " * 40 + "</p>"
                            for i in range(1, 151))),
    "attr_order": doc(plain(6, lambda i: (f'<a id="t{i}" href="#s{i}">{i} Section {i}</a>' if i % 2
                                          else f'<a href="#s{i}">{i} Section {i}</a>')),
                      "".join(sec(f"{i} Section {i}", f"s{i}") for i in range(1, 7))),
    "num_span": doc(plain(6, lambda i: f'<span class="n">{i}</span> <a href="#s{i}">Section {i}</a>'),
                    "".join(sec(f"{i} Section {i}", f"s{i}") for i in range(1, 7))),
    "nav_then_index": doc('<nav id="TOC">' + plain(4) + "</nav>",
                          "".join(sec(f"{i} Section {i}", f"s{i}") for i in range(1, 5))
                          + '<h2 id="idx">Index of figures</h2><ul><li><a href="#s2">Figure in section 2</a>.</li></ul>'),
}


def chrome_pdf(tmp_path, name, text):
    chrome = validation_report.find_browser()
    if not chrome:
        if os.environ.get("REQUIRE_CHROME") == "1":
            pytest.fail("REQUIRE_CHROME=1 but no Chrome or Chromium was found")
        pytest.skip("no Chrome or Chromium")
    src = tmp_path / f"{name}.html"
    src.write_text(text, encoding="utf-8")
    pdf = tmp_path / f"{name}.pdf"
    subprocess.run([chrome, "--headless", "--disable-gpu", "--no-sandbox", "--no-pdf-header-footer",
                    f"--print-to-pdf={pdf}", src.as_uri()], capture_output=True, timeout=180)
    assert pdf.is_file()
    return src, pdf


def entries(src):
    h = src.read_text(encoding="utf-8")
    start, end = T.contents_span(h)
    return [(e.group("t"), T.entry_title(e)) for e in T.ENTRY.finditer(h[start:end])]


@pytest.mark.parametrize("name", sorted(set(CASES) - {"nav_then_index"}))
def test_pages_found_by_text_are_the_pages_the_headings_print_on(tmp_path, name):
    src, pdf = chrome_pdf(tmp_path, name, CASES[name])
    es = entries(src)
    truth = T.dests(str(pdf))
    assert es and all(t in truth for t, _ in es), (es, truth)
    assert T.text_pages(str(pdf), es) == {t: truth[t] for t, _ in es}


def test_every_entry_is_numbered_whatever_the_link_s_attribute_order(tmp_path):
    src, pdf = chrome_pdf(tmp_path, "attr_order", CASES["attr_order"])
    out = tmp_path / "numbered.html"
    T.main(str(src), str(pdf), str(out))
    assert out.read_text(encoding="utf-8").count('class="toc-page"') == 6


def test_a_section_number_outside_the_link_stays_on_the_entry_s_line(tmp_path):
    src, pdf = chrome_pdf(tmp_path, "num_span", CASES["num_span"])
    out = tmp_path / "numbered.html"
    T.main(str(src), str(pdf), str(out))
    lines = re.findall(r'<span class="toc-line">.*?</span></span>', out.read_text(encoding="utf-8"), re.S)
    assert len(lines) == 6 and all('<span class="n">' in l for l in lines)


def test_the_contents_is_the_list_right_after_its_heading_and_nothing_later():
    """NIEM NDR v6.0 OS: the contents heading is followed by a <nav>, and the
    search ran on past it to number Appendix C's list of rules instead."""
    h = CASES["nav_then_index"]
    start, end = T.contents_span(h)
    assert [e.group("t") for e in T.ENTRY.finditer(h[start:end])] == ["s1", "s2", "s3", "s4"]
    assert "Figure" not in h[start:end]
    with pytest.raises(LookupError):
        T.contents_span('<h1 id="table-of-contents">Table of Contents</h1><p>none</p><h2>A</h2><ul><li>x</li></ul>')


@pytest.mark.parametrize("between", ['\n<tocHere/>\n<nav id="TOC">\n', "\n<!-- ToC template\n- [1 Scope](#1-scope)\n-->\n",
                                     '\n</summary>\n<div class="toc">\n'])
def test_real_contents_wrappers_are_accepted(between):
    """NIEM NDR v6.0 OS, ACAL core v1.0 csd01 and OData v4.02 csd02."""
    h = f'{H}{between}<ul><li><a href="#a">1 A</a></li><li><a href="#b">2 B</a></li></ul>'
    start, end = T.contents_span(h)
    assert [e.group("t") for e in T.ENTRY.finditer(h[start:end])] == ["a", "b"]


def test_a_wrapped_entry_ends_its_last_line_with_the_page_number(tmp_path):
    """DMLex F.1.1 wraps onto a second line; the number printed on the first
    line and the leader ran along the second to nothing. A published OASIS
    PDF ends the last line with the number (Sep 2026)."""
    long = "Tracking of changes made during the OASIS publishing process after the Public Reviews of the draft"
    text = doc(plain(3, lambda i: f'<a href="#s{i}">{i} {long if i == 2 else f"Section {i}"}</a>'),
               "".join(sec(f"{i} {long if i == 2 else f'Section {i}'}", f"s{i}") for i in range(1, 4)))
    src, pdf = chrome_pdf(tmp_path, "wrapped", text)
    out = tmp_path / "numbered.html"
    T.main(str(src), str(pdf), str(out))
    _, printed = chrome_pdf(tmp_path, "numbered", out.read_text(encoding="utf-8"))
    page = subprocess.run(["pdftotext", "-layout", "-f", "2", "-l", "2", str(printed), "-"],
                          capture_output=True, text=True).stdout
    lines = [l.rstrip() for l in page.splitlines() if l.strip()]
    first = next(i for i, l in enumerate(lines) if "2 Tracking of changes" in l)
    assert not re.search(r"\s\d+$", lines[first]), lines[first]
    assert "draft" in lines[first + 1] and re.search(r"\s\d+$", lines[first + 1]), lines[first:first + 2]
