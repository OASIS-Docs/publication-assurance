# Copyright 2026 OASIS Open
# SPDX-License-Identifier: Apache-2.0
# Authored by Michael Coletta, Technical Advisor to OASIS Open.
"""fence-collapse: the published HTML decides whether a fence collapsed.

A fence whose info string carries trailing text (```yaml <!--json-path-->)
collapses to inline code under pandoc's default markdown reader and renders
as a code block under its gfm and commonmark readers. CSAF v2.1 csd03 (Sep
2026) has 96 such fences; its HTML publishes every one as a <pre> block, and
the check reported 96 BLOCKERs. Where the HTML shows the block rendered, the
finding is one INFO about the Markdown's portability (a WARN until Oct 2026:
nothing in such a package is wrong, and the OASIS pipeline's step 1 rewrites
these fences before pandoc reads them). Where the HTML shows
it collapsed, or there is no HTML, it stays a BLOCKER per fence.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess

import pytest
from conftest import oasis_pub_check

MD = ("# 1 Intro\n\n```yaml <!--json-path($.a)-->\na: 1\n```\n\n"
      "Text.\n\n```json\n{\"b\": 2}\n```\n")
RENDERED = ('<h1>1 Intro</h1><pre class="yaml"><code>a: 1</code></pre>'
            '<p>Text.</p><pre><code>{&quot;b&quot;: 2}</code></pre>')
COLLAPSED = ('<h1>1 Intro</h1><p><code>yaml &lt;!--json-path($.a)--&gt; a: 1</code></p>'
             '<p>Text.</p><pre><code>{&quot;b&quot;: 2}</code></pre>')


def findings(md, html=""):
    f = oasis_pub_check.Findings()
    oasis_pub_check.check_md_fences(md, f, html)
    return [(x["severity"], x["message"]) for x in f.items if x["check"] == "fence-collapse"]


def test_a_block_the_html_publishes_as_code_is_a_portability_info():
    got = findings(MD, RENDERED)
    assert [s for s, _ in got] == ["INFO"]
    assert "lines 3)" in got[0][1] and "gfm or commonmark reader" in got[0][1]
    assert "no action is needed" in got[0][1]


def test_a_block_the_html_shows_collapsed_blocks():
    got = findings(MD, COLLAPSED)
    assert [s for s, _ in got] == ["BLOCKER"]
    assert "Line 3" in got[0][1] and "does not carry it as a code block" in got[0][1]


def test_without_html_the_collapse_is_still_a_blocker():
    got = findings(MD)
    assert [s for s, _ in got] == ["BLOCKER"] and "Line 3" in got[0][1]


def test_a_pre_already_matched_by_a_well_formed_fence_is_not_credited_twice():
    """The same code twice: once behind a clean fence, once behind a flagged
    one. One <pre> in the HTML is the clean fence's, so the flagged fence
    collapsed."""
    md = "```yaml\na: 1\n```\n\n```yaml <!-- note -->\na: 1\n```\n"
    got = findings(md, "<pre>a: 1</pre><p><code>yaml a: 1</code></p>")
    assert [s for s, _ in got] == ["BLOCKER"] and "Line 5" in got[0][1]
    assert [s for s, _ in findings(md, "<pre>a: 1</pre><pre>a: 1</pre>")] == ["INFO"]


def test_well_formed_fences_draw_nothing():
    md = "```yaml\na: 1\n```\n\n```{.yaml title=\"x\"}\nb: 2\n```\n"
    assert findings(md, "<pre>a: 1</pre><pre>b: 2</pre>") == []
    assert findings(md) == []


# The remedy the check prints must be one every reader renders. CSAF v2.1
# csd04 (22 Oct 2026) authors its Markdown for GitHub; the check told it to
# use ```{.lang title="..."}, which gfm and commonmark read as the language
# name "{.lang" (pandoc 3.8.2.1 renders <pre class="{.yaml">; GitHub
# highlights it as MiniYAML). An HTML
# comment on its own line above a plain ```lang fence renders as code under
# all three readers and keeps the note.
PORTABLE = "Intro.\n\n<!--json-path($.a)-->\n```yaml\na: 1\n```\n\nAfter.\n"
CURLY = "Intro.\n\n```{.yaml title=\"x\"}\na: 1\n```\n\nAfter.\n"


def test_the_info_recommends_a_form_every_reader_renders():
    (sev, msg), = findings(MD, RENDERED)
    assert sev == "INFO"
    assert "on its own line above the fence" in msg
    assert "pandoc only" in msg


def test_the_blocker_recommends_the_same_portable_form():
    (sev, msg), = findings(MD)
    assert sev == "BLOCKER"
    assert "on its own line above the fence" in msg


def test_the_info_says_the_oasis_pipeline_rewrites_the_fence_before_pandoc():
    """publisher-toolkit's step 1 has rewritten these fences before pandoc
    since v0.2.0 (lib/preprocess_md.py, 13 May 2026): on CSAF v2.1 csd04 it
    renders 726 <pre> blocks and collapses none, and drops the trailing
    json-path comment. Only pandoc's markdown reader run on its own collapses
    them."""
    (_, msg), = findings(MD, RENDERED)
    assert "(the OASIS pipeline's step 1) collapses" not in msg
    assert "step 1 rewrites these fences before pandoc reads them" in msg
    assert "dropping the trailing text" in msg


_PANDOC = pytest.mark.skipif(
    shutil.which("pandoc") is None and not os.environ.get("REQUIRE_PANDOC"),
    reason="pandoc is not installed (CI sets REQUIRE_PANDOC=1)")


def _pandoc(md, reader):
    return subprocess.run(["pandoc", "-f", reader, "-t", "html"], input=md,
                          capture_output=True, text=True, check=True).stdout


@_PANDOC
@pytest.mark.parametrize("reader", ["markdown", "gfm", "commonmark"])
def test_the_recommended_form_renders_as_yaml_code_under_every_reader(reader):
    html = _pandoc(PORTABLE, reader)
    assert "<pre" in html and 'class="sourceCode yaml"' in html
    assert "<code>yaml" not in html
    assert check_clean(PORTABLE)


@_PANDOC
@pytest.mark.parametrize("reader", ["gfm", "commonmark"])
def test_the_curly_form_loses_the_language_under_gfm_and_commonmark(reader):
    """Why the check no longer offers the curly form as the remedy: the
    reader takes '{.yaml' as the language name (pandoc 3.8.2.1 writes
    class="sourceCode {.yaml"; GitHub's /markdown API, 22 Oct 2026,
    highlights it as MiniYAML rather than YAML)."""
    assert '{.yaml"' in _pandoc(CURLY, reader)


def test_the_messages_survive_a_markdown_table_cell():
    """Reports put each message in a Markdown table cell. A raw <!-- -->
    vanishes there, and two runs of three backticks pair into one code span
    that swallows the text between them (GitHub /markdown, 22 Oct 2026).
    The BLOCKER's quote of the source's own info string is left out."""
    for _, msg in findings(MD, RENDERED) + findings(MD):
        own = re.sub(r"\('.*?\.\.\.'\)", "", msg)
        assert "<!--" not in own and own.count("```") <= 1


def check_clean(md):
    return findings(md) == []
