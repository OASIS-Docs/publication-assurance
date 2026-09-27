# Copyright 2026 OASIS Open
# SPDX-License-Identifier: Apache-2.0
# Authored by Michael Coletta, Technical Advisor to OASIS Open.
"""verify/verify_pdf.py: a rendered PDF against the published PDF, every word.

The DMLex Markdown edition's first renders (Sep 2026) printed contents with
no page numbers and numbered section 2's lettered lists 1., 2., 3.; the HTML
comparison passed both, since an HTML contents list has no page numbers and
list letters are not text. A side-by-side of the contents page, looked at by
a reviewer, passed it too. These PDFs are small documents printed by Chrome,
each case the smallest that shows one of those faults.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys

import pytest

from conftest import REPO_ROOT

sys.path.insert(0, str(REPO_ROOT / "pub-check"))
import validation_report  # noqa: E402

VERIFY = REPO_ROOT / "verify" / "verify_pdf.py"

pytestmark = pytest.mark.skipif(not shutil.which("pdftotext"), reason="poppler (pdftotext) is not installed")

INTRO = ["This specification defines the widget data model and its serializations.",
         "Implementations exchange widgets between applications without loss."]
BODY = ["A widget has a name, a version and zero or more parts.",
        "Each part refers to exactly one widget by its identifier.",
        "Parts are listed in the order in which they are assembled."]


def printed(tmp_path, name, pages, footer=True):
    """A PDF of the given pages (lists of lines, set in <pre> so each line
    prints as written), each ending with the running footer."""
    chrome = validation_report.find_browser()
    if not chrome:
        if os.environ.get("REQUIRE_CHROME") == "1":
            pytest.fail("REQUIRE_CHROME=1 but no Chrome or Chromium was found")
        pytest.skip("no Chrome or Chromium")
    body = ""
    for n, lines in enumerate(pages, 1):
        foot = (f"\n\nwidget-v1.0-csd01                                   1 May 2026\n"
                f"Standards Track Work Product   Copyright (c) OASIS Open 2026.   Page {n} of {len(pages)}"
                if footer else "")
        body += (f'<pre style="font: 11pt sans-serif; break-after: page">'
                 + "\n".join(lines).replace("&", "&amp;").replace("<", "&lt;") + foot + "</pre>")
    src = tmp_path / f"{name}.html"
    src.write_text(f"<html><body>{body}</body></html>", encoding="utf-8")
    pdf = tmp_path / f"{name}.pdf"
    subprocess.run([chrome, "--headless", "--disable-gpu", "--no-sandbox", "--no-pdf-header-footer",
                    f"--print-to-pdf={pdf}", src.as_uri()], capture_output=True, timeout=120)
    assert pdf.is_file() and pdf.stat().st_size > 800
    return pdf


def contents(numbers):
    rows = [("1 Introduction", 2), ("2 Widgets", 3), ("2.1 Parts", 3), ("3 Conformance", 4)]
    return ["Table of Contents"] + [f"{t} {'.' * 30} {n}" if numbers else t for t, n in rows]


def document(numbers=True, lettered=True, split=2):
    """Cover, contents, then the text, the page breaks after `split` body lines."""
    marks = ("a.", "b.") if lettered else ("1.", "2.")
    text = (["1 Introduction"] + INTRO + ["2 Widgets"] + BODY
            + ["3 Conformance", f"  {marks[0]} Conformant widgets MUST have a name.",
               f"  {marks[1]} Conformant parts MUST refer to a widget, as per point a. above."])
    return [["Widget Specification Version 1.0", "Committee Specification Draft 01"],
            contents(numbers), text[:split], text[split:]]


def verify(tmp_path, rendered, published, *allow):
    out = tmp_path / "report.json"
    args = [sys.executable, str(VERIFY), str(rendered), str(published), "--json", str(out)]
    for a in allow:
        path = tmp_path / f"allow{len(list(tmp_path.glob('allow*.json')))}.json"
        path.write_text(json.dumps(a), encoding="utf-8")
        args += ["--allow", str(path)]
    r = subprocess.run(args, capture_output=True, text=True)
    return r, json.loads(out.read_text(encoding="utf-8")) if out.exists() else {}


def test_the_same_document_paginated_differently_passes(tmp_path):
    pub = printed(tmp_path, "pub", document(split=2))
    ren = printed(tmp_path, "ren", document(split=6))
    r, rep = verify(tmp_path, ren, pub)
    assert r.returncode == 0, r.stdout
    assert rep["contents_numbered_published"] == rep["contents_numbered_rendered"] == 4
    assert rep["diff_regions"] == 0 and rep["published_tokens"] > 100


def test_contents_without_page_numbers_fail(tmp_path):
    """The miss that started this: every entry numbered in the publication, none in the render."""
    pub = printed(tmp_path, "pub", document())
    ren = printed(tmp_path, "ren", document(numbers=False))
    r, rep = verify(tmp_path, ren, pub)
    assert r.returncode == 1
    assert rep["contents_numbered_rendered"] == 0 and rep["contents_entries_rendered"] == 4
    assert sum(d["published"].endswith("<page>") and "<page>" not in d["markdown"] for d in rep["diffs"]) >= 1
    assert sum(d["published"].count("<page>") for d in rep["diffs"]) == 4


def test_a_lettered_list_printed_with_numbers_fails(tmp_path):
    pub = printed(tmp_path, "pub", document())
    ren = printed(tmp_path, "ren", document(lettered=False))
    r, rep = verify(tmp_path, ren, pub)
    assert r.returncode == 1
    assert {"a", "b"} <= set(" ".join(d["published"] for d in rep["diffs"]).split())
    assert {"1", "2"} <= set(" ".join(d["markdown"] for d in rep["diffs"]).split())


def test_a_page_without_the_running_footer_fails(tmp_path):
    pub = printed(tmp_path, "pub", document())
    ren = printed(tmp_path, "ren", document(), footer=False)
    r, rep = verify(tmp_path, ren, pub)
    assert r.returncode == 1
    assert rep["running_lines_rendered"] == [] and len(rep["rendered_pages_without_running_line"]) == 4


def test_a_word_hyphenated_across_lines_is_line_wrapping(tmp_path):
    pages = document()
    pub_pages = [list(p) for p in pages]
    pub_pages[2] = [x.replace("the widget data model", "the widget da-\nta model") for x in pub_pages[2]]
    pub = printed(tmp_path, "pub", pub_pages)
    ren = printed(tmp_path, "ren", pages)
    r, rep = verify(tmp_path, ren, pub)
    assert r.returncode == 0, r.stdout
    assert rep["line_wrap_regions"] == 1


def test_a_changed_word_fails_and_an_allow_rule_accepts_it_once(tmp_path):
    pages = document()
    changed = [list(p) for p in pages]
    changed[2] = [x.replace("widget data model", "gadget data model") for x in changed[2]]
    pub = printed(tmp_path, "pub", pages)
    ren = printed(tmp_path, "ren", changed)
    r, rep = verify(tmp_path, ren, pub)
    assert r.returncode == 1 and [(d["published"], d["markdown"]) for d in rep["diffs"]] == [("widget", "gadget")]
    rule = {"published": "widget", "markdown": "gadget", "reason": "the TC renamed it"}
    r, rep = verify(tmp_path, ren, pub, [rule])
    assert r.returncode == 0 and rep["accepted_deviations"] == 1
    r, rep = verify(tmp_path, pub, pub, [rule])
    assert r.returncode == 1 and rep["allow_rules_unused"] == [rule], "a rule that accepts nothing fails"


def test_a_footer_rule_accepts_a_different_running_line(tmp_path):
    pages = document()
    pub = printed(tmp_path, "pub", pages)
    ren_src = printed(tmp_path, "ren", pages)
    html = (tmp_path / "ren.html").read_text(encoding="utf-8").replace("Copyright (c)", "Copyright &#169;")
    (tmp_path / "ren.html").write_text(html, encoding="utf-8")
    chrome = validation_report.find_browser()
    subprocess.run([chrome, "--headless", "--disable-gpu", "--no-sandbox", "--no-pdf-header-footer",
                    f"--print-to-pdf={ren_src}", (tmp_path / "ren.html").as_uri()], capture_output=True, timeout=120)
    r, rep = verify(tmp_path, ren_src, pub)
    assert r.returncode == 1 and len(rep["running_lines_only_published"]) == 1
    rule = {"kind": "footer", "published": rep["running_lines_only_published"][0],
            "markdown": rep["running_lines_only_rendered"][0], "reason": "the document's own copyright sign"}
    r, rep = verify(tmp_path, ren_src, pub, [rule])
    assert r.returncode == 0, r.stdout
