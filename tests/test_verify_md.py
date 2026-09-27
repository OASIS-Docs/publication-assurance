# Copyright 2026 OASIS Open
# SPDX-License-Identifier: Apache-2.0
# Authored by Michael Coletta, Technical Advisor to OASIS Open.
"""verify/verify_md.py: a Markdown edition against the published HTML.

The fixture is the Markdown edition of DMLex Version 1.0 OASIS Standard
(MColetta-OASIS/lexidma, branch markdown-conversion) and a copy of
https://docs.oasis-open.org/lexidma/dmlex/v1.0/os/dmlex-v1.0-os.html fetched
on 27 September 2026 (sha256 3f533a53...). With the DMLex allow file the two
agree on all 61,260 published tokens, 311 headings and 316 code blocks. A
verifier that passes an altered copy, or passes on nothing, proves nothing,
so both are tested.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request

import pytest

from conftest import FIXTURES, REPO_ROOT

VERIFY = REPO_ROOT / "verify" / "verify_md.py"
DMLEX = FIXTURES / "verify_md" / "dmlex-v1.0-os"
MD = DMLEX / "dmlex-v1.0-os.md"
PUBLISHED = DMLEX / "published-dmlex-v1.0-os.html"
ALLOW = REPO_ROOT / "converters" / "docbook-to-markdown" / "profiles" / "dmlex" / "allow.json"
LIVE = "https://docs.oasis-open.org/lexidma/dmlex/v1.0/os/dmlex-v1.0-os.html"

pytestmark = pytest.mark.skipif(
    shutil.which("pandoc") is None and not os.environ.get("REQUIRE_PANDOC"),
    reason="pandoc is not installed (CI sets REQUIRE_PANDOC=1)")


def verify(md, html, tmp_path, *extra, allow=ALLOW, root=None):
    out = tmp_path / "report.json"
    args = [sys.executable, str(VERIFY), str(md), str(html), "--json", str(out),
            "--root", str(root or md.parent)]
    if allow:
        args += ["--allow", str(allow)]
    r = subprocess.run(args + list(extra), capture_output=True, text=True)
    report = json.loads(out.read_text(encoding="utf-8")) if out.exists() else {}
    return r, report


def altered(tmp_path, old, new, count=1):
    """A copy of the DMLex edition with one edit, images and all."""
    dst = tmp_path / "md"
    shutil.copytree(DMLEX, dst)
    md = dst / MD.name
    text = md.read_text(encoding="utf-8")
    assert text.count(old) >= count, f"fixture no longer contains {old!r}"
    md.write_text(text.replace(old, new, count), encoding="utf-8")
    return md


def test_the_dmlex_edition_matches_the_published_os(tmp_path):
    r, rep = verify(MD, PUBLISHED, tmp_path)
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr
    assert r.stdout.rstrip().endswith("RESULT: PASS")
    assert rep["diff_regions"] == 0 and rep["accepted_deviations"] == 10
    assert rep["allow_rules_unused"] == []
    assert rep["list_items_published"] == rep["list_items_markdown"] == 1133
    assert int(rep["pandoc"].split(".")[0]) >= 3
    assert rep["published_tokens"] == 61260
    assert rep["headings_published"] == 311 and rep["headings_missing"] == []
    assert rep["code_blocks_published"] == rep["code_blocks_markdown"] == 316
    assert rep["code_blocks_differing"] == []
    assert rep["images_published"] == rep["images_markdown"] == 50
    assert rep["broken_internal_links"] == [] and rep["internal_links"] > 3000


def test_the_live_published_page_is_accepted_by_url(tmp_path):
    try:
        urllib.request.urlopen(LIVE, timeout=20).close()
    except OSError:
        if os.environ.get("REQUIRE_NETWORK"):
            raise
        pytest.skip("docs.oasis-open.org is not reachable (CI sets REQUIRE_NETWORK=1)")
    r, rep = verify(MD, LIVE, tmp_path)
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr
    assert rep["diff_regions"] == 0 and rep["published_tokens"] == 61260


def test_a_changed_word_fails_and_is_named(tmp_path):
    md = altered(tmp_path, "modelling dictionaries", "modelling lexicons")
    r, rep = verify(md, PUBLISHED, tmp_path)
    assert r.returncode == 1 and "RESULT: FAIL" in r.stdout
    assert [(d["published"], d["markdown"]) for d in rep["diffs"]] == [("dictionaries", "lexicons")], rep["diffs"]


def test_a_changed_code_block_fails(tmp_path):
    text = MD.read_text(encoding="utf-8")
    start = text.index("```json\n") + len("```json\n")
    block = text[start:text.index("```", start)]
    line = next(l for l in block.split("\n") if '"' in l)
    md = altered(tmp_path, line, line.replace('"', "'", 2))
    r, rep = verify(md, PUBLISHED, tmp_path)
    assert r.returncode == 1
    assert rep["code_blocks_differing"], "an edited code block was not reported"


def test_a_dropped_heading_and_a_missing_image_fail(tmp_path):
    md = altered(tmp_path, "## 3.1 Optional roots", "3.1 Optional roots")
    (md.parent / "dmlex_uml.svg").unlink()
    r, rep = verify(md, PUBLISHED, tmp_path)
    assert r.returncode == 1
    assert rep["images_missing_on_disk"] == ["dmlex_uml.svg"]
    assert any(h.startswith("3.1 ") for h in rep["headings_missing"]), rep["headings_missing"]


def test_without_the_allow_file_the_known_deviations_fail(tmp_path):
    r, rep = verify(MD, PUBLISHED, tmp_path, allow=None)
    assert r.returncode == 1 and rep["diff_regions"] == 10


def test_an_allow_rule_without_a_reason_is_refused(tmp_path):
    rules = json.loads(ALLOW.read_text(encoding="utf-8"))
    del rules[0]["reason"]
    bad = tmp_path / "allow.json"
    bad.write_text(json.dumps(rules), encoding="utf-8")
    r, _ = verify(MD, PUBLISHED, tmp_path, allow=bad)
    assert r.returncode == 2 and "reason" in r.stderr


def test_an_empty_document_does_not_pass(tmp_path):
    empty = tmp_path / "empty.md"
    empty.write_text("", encoding="utf-8")
    blank = tmp_path / "blank.html"
    blank.write_text("<html><body></body></html>", encoding="utf-8")
    r, _ = verify(empty, blank, tmp_path, allow=None, root=tmp_path)
    assert r.returncode != 0 and "RESULT: PASS" not in r.stdout


def test_cloudflare_obfuscated_emails_are_decoded(tmp_path):
    """docs.oasis-open.org is behind Cloudflare, which serves every address as
    "[email protected]" plus an XOR-encoded data-cfemail attribute. The
    snapshot carries seven; the passing run above decodes them. Without the
    payload the placeholders cannot match the Markdown's addresses."""
    html = PUBLISHED.read_text(encoding="latin-1")  # the page declares ISO-8859-1
    assert html.count('class="__cf_email__" data-cfemail=') == 7
    undecodable = re.sub(r' data-cfemail="[0-9a-f]+"', "", html)
    obf = tmp_path / "published.html"
    obf.write_text(undecodable, encoding="latin-1")
    r, rep = verify(MD, obf, tmp_path)
    assert r.returncode == 1 and len(rep["diffs"]) == 7, rep["diffs"]


def test_the_report_prints_every_difference_in_full(tmp_path):
    long = "x" * 400
    md = altered(tmp_path, "modelling dictionaries", f"modelling {long} dictionaries")
    r, _ = verify(md, PUBLISHED, tmp_path)
    assert long in r.stdout, "a difference was truncated in the printed report"


def test_the_first_heading_after_the_published_contents_is_compared(tmp_path):
    """The contents strip once ran past the DocBook div.toc into the
    Introduction heading, and an allow rule hid the loss."""
    md = altered(tmp_path, "# 1 Introduction (Normative)", "# 1 Preface (Normative)")
    r, rep = verify(md, PUBLISHED, tmp_path)
    assert r.returncode == 1
    assert any(d["published"] == "Introduction" and d["markdown"] == "Preface" for d in rep["diffs"]), rep["diffs"]


def test_an_allow_rule_accepts_only_as_many_differences_as_it_names(tmp_path):
    """The ':' rule is for the Notices label. The same deletion anywhere else
    is a real change and must be reported."""
    text = MD.read_text(encoding="utf-8")
    assert "Chair:" in text
    md = altered(tmp_path, "#### Chair:", "#### Chair")
    r, rep = verify(md, PUBLISHED, tmp_path)
    assert r.returncode == 1
    assert [d["published"] for d in rep["diffs"]] == [":"], rep["diffs"]


def test_an_unused_allow_rule_fails(tmp_path):
    """A rule that accepts nothing is either stale or half of a pair whose
    other half hid something: the Key words paragraph is allowed to move
    (a delete and an insert), not to vanish."""
    rules = json.loads(ALLOW.read_text(encoding="utf-8"))
    rules.append({"published": "never", "markdown": "seen", "reason": "a stale rule"})
    stale = tmp_path / "allow.json"
    stale.write_text(json.dumps(rules), encoding="utf-8")
    r, rep = verify(MD, PUBLISHED, tmp_path, allow=stale)
    assert r.returncode == 1 and "UNUSED ALLOW RULE" in r.stdout
    assert rep["allow_rules_unused"] == [rules[-1]]


def test_the_key_words_paragraph_may_move_but_not_vanish(tmp_path):
    text = MD.read_text(encoding="utf-8")
    start = text.index("#### Key words:")
    end = text.index("\n#### ", start + 1)
    md = altered(tmp_path, text[start:end], "")
    r, rep = verify(md, PUBLISHED, tmp_path)
    assert r.returncode == 1 and rep["allow_rules_unused"], rep["diffs"]


TABLE_HTML = ("<html><body><p>Values and meanings follow.</p><table><tr><th>Value</th><th>Meaning</th></tr>"
              "<tr><td>alpha</td><td>first</td></tr><tr><td>beta</td><td>second</td></tr></table>"
              "<ul><li>one item</li><li>two item</li></ul></body></html>")
TABLE_MD = ("Values and meanings follow.\n\n| Value | Meaning |\n|---|---|\n| alpha | first |\n"
            "| beta | second |\n\n- one item\n- two item\n")


def _pair(tmp_path, md_text):
    (tmp_path / "t.md").write_text(md_text, encoding="utf-8")
    (tmp_path / "t.html").write_text(TABLE_HTML, encoding="utf-8")
    return verify(tmp_path / "t.md", tmp_path / "t.html", tmp_path, allow=None)


def test_a_table_and_a_list_with_their_shape_pass(tmp_path):
    r, rep = _pair(tmp_path, TABLE_MD)
    assert r.returncode == 0, r.stdout
    assert rep["tables_published"] == rep["tables_markdown"] == [[["Value", "Meaning"], ["alpha", "first"], ["beta", "second"]]]


def test_a_table_flattened_into_paragraphs_fails(tmp_path):
    flat = TABLE_MD.replace("| Value | Meaning |\n|---|---|\n| alpha | first |\n| beta | second |",
                            "Value Meaning\n\nalpha first\n\nbeta second")
    r, rep = _pair(tmp_path, flat)
    assert r.returncode == 1 and rep["diff_regions"] == 0, "same words, so only the shape can catch it"
    assert rep["tables_markdown"] == []


def test_a_list_flattened_into_a_paragraph_fails(tmp_path):
    r, rep = _pair(tmp_path, TABLE_MD.replace("- one item\n- two item", "one item two item"))
    assert r.returncode == 1 and rep["diff_regions"] == 0
    assert (rep["list_items_published"], rep["list_items_markdown"]) == (2, 0)


def test_a_rule_without_a_count_accepts_one_difference(tmp_path):
    """'version' to 'stage' happens three times (This, Previous, Latest), so
    the DMLex rule says count 3. Without it, the other two are reported."""
    rules = json.loads(ALLOW.read_text(encoding="utf-8"))
    rule = next(r for r in rules if r["published"] == "version")
    assert rule.pop("count") == 3
    one = tmp_path / "allow.json"
    one.write_text(json.dumps(rules), encoding="utf-8")
    r, rep = verify(MD, PUBLISHED, tmp_path, allow=one)
    assert r.returncode == 1
    assert [(d["published"], d["markdown"]) for d in rep["diffs"]] == [("version", "stage")] * 2


def test_text_added_under_the_contents_heading_is_compared(tmp_path):
    md = altered(tmp_path, "\n---\n\n# 1 Introduction",
                 "\nNote: implementations MAY ignore the Conformance section.\n\n---\n\n# 1 Introduction")
    r, rep = verify(md, PUBLISHED, tmp_path)
    assert r.returncode == 1
    assert any("MAY ignore" in d["markdown"] for d in rep["diffs"]), rep["diffs"]


def test_an_image_commented_out_or_swapped_fails(tmp_path):
    img = '<img src="core/databaseDiagrams/entry.svg"'
    text = MD.read_text(encoding="utf-8")
    line = text[text.index(img):text.index(">", text.index(img)) + 1]
    md = altered(tmp_path, line, f"<!-- {line} -->")
    r, rep = verify(md, PUBLISHED, tmp_path)
    assert r.returncode == 1 and rep["images_differing"] == ["-core/databaseDiagrams/entry.svg"]
    md = altered(tmp_path / "b", line, line.replace("entry.svg", "sense.svg"))
    r, rep = verify(md, PUBLISHED, tmp_path)
    assert r.returncode == 1 and "+core/databaseDiagrams/sense.svg" in rep["images_differing"]


def test_a_changed_link_target_fails(tmp_path):
    md = altered(tmp_path, "(https://www.muni.cz/)", "(https://example.com/)")
    r, rep = verify(md, PUBLISHED, tmp_path)
    assert r.returncode == 1 and rep["diff_regions"] == 0
    diff = rep["external_links_differing"]
    assert {d["published"] for d in diff} - {""} == {"https://www.muni.cz/"}
    assert {d["markdown"] for d in diff} - {""} == {"https://example.com/"}


def test_hidden_or_struck_words_fail(tmp_path):
    for i, (old, new) in enumerate((("modelling dictionaries", "modelling ~~dictionaries~~"),
                                    ("modelling dictionaries", 'modelling <span style="display:none">dictionaries</span>'),
                                    ("modelling dictionaries", "modelling <header>no</header><head></head> dictionaries"))):
        md = altered(tmp_path / str(i), old, new)
        r, rep = verify(md, PUBLISHED, tmp_path)
        assert r.returncode == 1, (new, rep["diffs"], rep["hidden_or_struck_markdown"])


def test_code_indentation_and_a_missing_block_are_reported_once(tmp_path):
    text = MD.read_text(encoding="utf-8")
    start = text.index("```json\n") + len("```json\n")
    first = text[start:text.index("\n", start)]
    md = altered(tmp_path, "```json\n" + first, "```json\n    " + first)
    r, rep = verify(md, PUBLISHED, tmp_path)
    assert r.returncode == 1 and len(rep["code_blocks_differing"]) == 1
    end = text.index("```", start) + 3
    md = altered(tmp_path / "b", text[start - len("```json\n"):end], "")
    r, rep = verify(md, PUBLISHED, tmp_path)
    assert r.returncode == 1 and len(rep["code_blocks_differing"]) == 1, rep["code_blocks_differing"]
    assert rep["code_blocks_differing"][0]["op"] == "delete"


def test_a_word_moved_to_another_table_row_fails(tmp_path):
    html = TABLE_HTML.replace("<td>first</td>", "<td>first MUST</td>")
    (tmp_path / "t.html").write_text(html, encoding="utf-8")
    moved = TABLE_MD.replace("| alpha | first |\n| beta | second |", "| alpha | first |\n| MUST beta | second |")
    (tmp_path / "t.md").write_text(moved, encoding="utf-8")
    r, rep = verify(tmp_path / "t.md", tmp_path / "t.html", tmp_path, allow=None)
    assert rep["diff_regions"] == 0, "the words line up; only the rows show it"
    assert r.returncode == 1 and rep["tables_published"] != rep["tables_markdown"]


def test_the_charset_comes_from_the_page_the_server_or_the_html_default(tmp_path):
    html = PUBLISHED.read_bytes()
    bare = tmp_path / "bare.html"
    bare.write_bytes(re.sub(rb'<meta http-equiv="Content-Type"[^>]*>', b"", html, count=1))
    assert b"charset" not in bare.read_bytes()[:2000]
    r, rep = verify(MD, bare, tmp_path)
    assert r.returncode == 0, rep.get("diffs")
    odd = tmp_path / "odd.html"
    odd.write_bytes(html.replace(b"charset=ISO-8859-1", b"charset=no-such-charset", 1))
    r, _ = verify(MD, odd, tmp_path)
    assert r.returncode == 2 and "unknown charset" in r.stderr


def test_a_url_is_decoded_with_the_server_charset(tmp_path):
    import http.server
    import threading
    body = re.sub(rb'<meta http-equiv="Content-Type"[^>]*>', b"", PUBLISHED.read_bytes(), count=1)

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=ISO-8859-1")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *a):
            pass
    srv = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        r, rep = verify(MD, f"http://127.0.0.1:{srv.server_port}/dmlex.html", tmp_path)
    finally:
        srv.shutdown()
    assert r.returncode == 0, rep.get("diffs")
