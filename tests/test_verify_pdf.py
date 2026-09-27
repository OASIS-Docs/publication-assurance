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


# The comparison itself, on pages given as lines: each case isolates one rule.
# The first four are the adversarial review's counterexamples (Sep 2026), each
# of which printed RESULT: PASS before the rule was tightened.
sys.path.insert(0, str(REPO_ROOT / "verify"))
import verify_pdf as VP  # noqa: E402

BASE = ["The client waits and then retries the request.", "The timeout is 30 seconds with 5 retries.",
        "The client MUST NOT retry. The server MUST cache the response."]
OTHER = ["Each lexicographic resource holds entries and their senses.",
         "A sense carries definitions, examples and translations.",
         "Relations link entries from other resources as well."]


def pages(*bodies, footer="widget-v1.0-csd01   1 May 2026"):
    """Pages of body lines, each ending with the two running footer lines. A
    single body gets a second page of other text: a running line needs two
    pages, and text that repeats on every page would itself read as one."""
    if len(bodies) == 1:
        bodies = bodies + (OTHER,)
    n = len(bodies)
    return [list(b) + [footer, f"Standards Track Work Product   Copyright OASIS Open 2026.   Page {k} of {n}"]
            for k, b in enumerate(bodies, 1)]


def run_pages(pub, ren, rules=()):
    rep = VP.compare(pub, ren, list(rules))
    return VP.passed(rep), rep


def test_swapped_numbers_are_a_difference_not_a_reordering():
    ok, rep = run_pages(pages(BASE), pages([BASE[0], "The timeout is 5 seconds with 30 retries.", BASE[2]]))
    assert not ok and rep["diff_regions"] >= 1


def test_a_moved_not_is_a_difference():
    ok, _ = run_pages(pages(BASE), pages([BASE[0], BASE[1], "The client MUST retry. The server MUST NOT cache the response."]))
    assert not ok


def test_a_lost_minus_sign_is_a_difference_but_a_line_end_hyphen_is_wrapping():
    ok, _ = run_pages(pages(["The offset is -1 from the start."]), pages(["The offset is 1 from the start."]))
    assert not ok
    ok, _ = run_pages(pages(["The offset is -", "1 from the start."]), pages(["The offset is 1 from the start."]))
    assert not ok, "a hyphen that ends a line before a digit is a minus sign, not a word break"
    ok, rep = run_pages(pages(["The data model is vali-", "dated by the schema."]),
                        pages(["The data model is validated by the schema."]))
    assert ok and rep["line_wrap_regions"] == 1


def test_a_footer_with_the_wrong_version_or_date_is_a_difference():
    ok, rep = run_pages(pages(BASE), pages(BASE, footer="widget-v2.0-csd02   9 May 2024"))
    assert not ok and rep["running_lines_only_rendered"] == ["widget-v2.0-csd02 9 May 2024"]
    ok, rep = run_pages(pages(BASE, OTHER), pages(BASE, OTHER[:2], OTHER[2:]))
    assert ok, "page numbers and the page count may differ"


def test_every_rendered_page_must_carry_the_running_line():
    ren = pages(BASE, OTHER, BASE[::-1])
    ren[1] = ren[1][:-2]
    ok, rep = run_pages(pages(BASE, OTHER, BASE[::-1]), ren)
    assert not ok and rep["rendered_pages_without_running_line"] == [2]


def test_a_block_moved_unchanged_is_counted_and_a_changed_one_is_not():
    cap = "Example 12. Relational database layout"
    ok, rep = run_pages(pages([cap] + BASE), pages(BASE[:1] + [cap] + BASE[1:]))
    assert ok and rep["moved_blocks"] == 1
    ok, _ = run_pages(pages([cap] + BASE), pages(BASE[:1] + ["Example 13. Relational database layout"] + BASE[1:]))
    assert not ok


def test_bullets_and_ligatures_are_layout():
    ok, _ = run_pages(pages(["\u2022 the definition of a sense"]), pages(["the de\ufb01nition of a sense"]))
    assert ok
    ok, _ = run_pages(pages(["the definition of a sense"]), pages(["the defintion of a sense"]))
    assert not ok


def test_a_wrapped_contents_entry_carries_its_number_on_its_last_line():
    toc = ["Table of Contents", "1 Introduction ........ 2", "2 Tracking of changes made during the publishing",
           "process after Public Reviews ........ 3", "3 Conformance ........ 4"]
    body = ["1 Introduction", "2 Tracking of changes made during the publishing process after Public Reviews",
            "3 Conformance"]
    ok, rep = run_pages(pages(toc, body), pages(toc, body))
    assert ok and rep["contents_numbered_published"] == 3
    unnumbered = toc[:3] + ["process after Public Reviews"] + toc[4:]
    ok, rep = run_pages(pages(toc, body), pages(unnumbered, body))
    assert not ok and rep["contents_numbered_rendered"] == 2


def test_a_declared_region_compares_characters_not_order():
    fig = ["Figure 1", "core@title: 0..1   core@uri: 0..1", "entry   sense   example"]
    moved = ["Figure 1", "entry   sense   example", "core@uri: 0..1   core@title: 0..1"]
    region = {"kind": "region", "from": "Figure 1", "to": "Next section", "reason": "regenerated diagram"}
    ok, _ = run_pages(pages(fig + ["Next section"] + BASE), pages(moved + ["Next section"] + BASE))
    assert not ok, "without the region, reordered labels are differences"
    ok, rep = run_pages(pages(fig + ["Next section"] + BASE), pages(moved + ["Next section"] + BASE), [region])
    assert ok and rep["regions_compared"] == 1
    changed = ["Figure 1", "entry   sense   example", "core@uri: 0..1   core@title: 1..1"]
    ok, _ = run_pages(pages(fig + ["Next section"] + BASE), pages(changed + ["Next section"] + BASE), [region])
    assert not ok, "inside the region a changed multiplicity still counts"


def test_a_rule_matches_a_difference_that_pdftotext_split_in_two():
    """Ubuntu's pdftotext split DMLex's "Example A.64. RDF" caption around a
    word of the code beside it; poppler 26 printed it whole. The same rule
    must accept both, and still nothing more."""
    pub = pages(["Example 7. RDF ex:lexicon a dmlex:Resource ;", "dmlex:hint dmlex:navigate ;"])
    ren = pages(["ex:lexicon a dmlex:Resource ;", "dmlex:hint dmlex:navigate ;"])
    whole = {"published": "Example 7 . RDF", "markdown": "", "reason": "caption printed on a code line"}
    ok, rep = run_pages(pub, ren, [whole])
    assert ok, rep["diffs"]
    split = pages(["Example 7. ex:lexicon a RDF dmlex:Resource ;", "dmlex:hint dmlex:navigate ;"])
    ok, rep = run_pages(split, ren, [whole])
    assert ok, rep["diffs"]
    far = pages(["Example 7. ex:lexicon a dmlex:Resource ; dmlex:hint dmlex:navigate ; and a long run of",
                 "other words that are the same on both sides before the stray RDF appears"])
    ok, _ = run_pages(far, pages(["ex:lexicon a dmlex:Resource ; dmlex:hint dmlex:navigate ; and a long run of",
                                  "other words that are the same on both sides before the stray appears"]), [whole])
    assert not ok, "pieces far apart are two differences, not one split"
