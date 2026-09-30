# Copyright 2026 OASIS Open
# SPDX-License-Identifier: Apache-2.0
# Authored by Michael Coletta, Technical Advisor to OASIS Open.
"""fence-collapse: the published HTML decides whether a fence collapsed.

A fence whose info string carries trailing text (```yaml <!--json-path-->)
collapses to inline code under pandoc's default markdown reader and renders
as a code block under its gfm and commonmark readers. CSAF v2.1 csd03 (Sep
2026) has 96 such fences; its HTML publishes every one as a <pre> block, and
the check reported 96 BLOCKERs. Where the HTML shows the block rendered, the
finding is one WARN about the Markdown's portability. Where the HTML shows
it collapsed, or there is no HTML, it stays a BLOCKER per fence.
"""

from __future__ import annotations

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


def test_a_block_the_html_publishes_as_code_is_a_portability_warn():
    got = findings(MD, RENDERED)
    assert [s for s, _ in got] == ["WARN"]
    assert "lines 3)" in got[0][1] and "gfm/commonmark reader" in got[0][1]


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
    assert [s for s, _ in findings(md, "<pre>a: 1</pre><pre>a: 1</pre>")] == ["WARN"]


def test_well_formed_fences_draw_nothing():
    md = "```yaml\na: 1\n```\n\n```{.yaml title=\"x\"}\nb: 2\n```\n"
    assert findings(md, "<pre>a: 1</pre><pre>b: 2</pre>") == []
    assert findings(md) == []
