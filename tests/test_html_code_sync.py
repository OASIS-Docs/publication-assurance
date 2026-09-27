# Copyright 2026 OASIS Open
# SPDX-License-Identifier: Apache-2.0
# Authored by Michael Coletta, Technical Advisor to OASIS Open.
"""html-code-sync: the HTML publishes the Markdown's code blocks unchanged.

The DMLex v1.0 OS Markdown edition, rendered by the pipeline's step 1 before
--preserve-tabs, published 9 of its 316 code blocks with their tabs expanded.
Every CSAF corpus package's HTML matches its Markdown's blocks exactly.
"""

from __future__ import annotations

import pytest

from conftest import CORPUS, oasis_pub_check

MD = "# 1 Intro\n\n```json\n{\n\t\"a\": 1\n}\n```\n\nText.\n\n```\nplain\n```\n"
HTML_OK = '<h1>1 Intro</h1><pre><code class="json">{\n\t&quot;a&quot;: 1\n}</code></pre><p>Text.</p><pre>plain</pre>'


def findings(md, html):
    f = oasis_pub_check.Findings()
    oasis_pub_check.check_html_code_sync(md, html, f)
    return [(x["severity"], x["message"]) for x in f.items if x["check"] == "html-code-sync"]


def test_identical_code_blocks_pass():
    assert findings(MD, HTML_OK) == []


def test_expanded_tabs_warn_with_the_markdown_line():
    got = findings(MD, HTML_OK.replace("\t", "    "))
    assert [s for s, _ in got] == ["WARN"] and "line 3" in got[0][1]


def test_changed_code_blocks():
    got = findings(MD, HTML_OK.replace("1\n}", "2\n}"))
    assert [s for s, _ in got] == ["BLOCKER"] and "line 3" in got[0][1]


def test_a_missing_block_blocks():
    got = findings(MD, HTML_OK.replace("<pre>plain</pre>", "<p>plain</p>"))
    assert [s for s, _ in got] == ["BLOCKER"] and "'plain'" in got[0][1]


def test_extra_pre_blocks_in_the_html_are_not_findings():
    assert findings(MD, HTML_OK + "<pre>an indented block</pre>") == []


def test_a_fence_inside_a_longer_fence_is_content():
    md = "````\n```\ninner\n```\n````\n"
    assert findings(md, "<pre>```\ninner\n```</pre>") == []


@pytest.mark.parametrize("rel", ["csaf/v2.0/os", "csaf/v2.1/csd01"])
def test_the_corpus_publishes_its_code_unchanged(rel):
    stage = CORPUS / rel
    md = next(p for p in stage.glob("*.md") if not p.name.endswith("README.md"))
    html = md.with_suffix(".html")
    f = oasis_pub_check.Findings()
    oasis_pub_check.check_html_code_sync(md.read_text(encoding="utf-8"), html.read_text(encoding="utf-8"), f)
    assert [x for x in f.items if x["check"] == "html-code-sync"] == []
    assert int(f.observed["html-code-sync"]["markdown_fenced_blocks"]) > 300, "a vacuous corpus comparison"


def test_a_comment_inside_code_is_code_and_a_fence_inside_a_comment_is_not():
    md = "<!--\n```\nold\n```\n-->\n\n```xml\n<a>\n  <!-- ... -->\n</a>\n```\n"
    assert findings(md, "<pre>&lt;a&gt;\n  &lt;!-- ... --&gt;\n&lt;/a&gt;</pre>") == []


def test_a_diagram_fence_is_not_compared_and_list_tabs_are_whitespace():
    md = "```dot\ndigraph G { a -> b }\n```\n\n1. step\n   ```xml\n   <a>\n\t\t<b/>\n\t </a>\n   ```\n"
    got = findings(md, '<img src="g.svg"><ol><li>step<pre>&lt;a&gt;\n     &lt;b/&gt;\n  &lt;/a&gt;</pre></li></ol>')
    assert [s for s, _ in got] == ["WARN"], got
