# Copyright 2026 OASIS Open
# SPDX-License-Identifier: Apache-2.0
# Authored by Michael Coletta, Technical Advisor to OASIS Open.
"""html-residue: pandoc caption and attribute syntax printed as text.

CSAF v2.1 csd03 (Sep 2026) publishes five paragraphs like
"Table: Remediation Combinations{#vulnerabilities-property-remediations-category-tab-1}":
the renderer did not read the pandoc table caption, so readers see the raw
Markdown and the id is missing, which leaves the links to it dangling.
"""

from __future__ import annotations

import pytest

from conftest import oasis_pub_check


def residue(html):
    f = oasis_pub_check.Findings()
    oasis_pub_check.check_html("<title>Widget Version 1.0</title><a href='#x'>x</a><p id='x'></p>"
                               + html, "wid-v1.0-csd01", f)
    return [(x["severity"], x["message"]) for x in f.items
            if x["check"] == "html-residue" and "caption or attribute syntax" in x["message"]]


def test_a_leaked_table_caption_with_its_id_blocks():
    got = residue("<table></table><p>Table: Remediation <code>category</code> Combinations{#rem-tab-1}</p>")
    assert [s for s, _ in got] == ["BLOCKER"]
    assert "'Table: Remediation category Combinations{#rem-tab-1}'" in got[0][1]


def test_an_attribute_block_ending_a_block_blocks_with_or_without_a_caption():
    got = residue("<h2>Scope {#scope}</h2><p>Some text{#anchor-1 .unnumbered}</p>"
                  "<p>Figure: The widget{#fig-1}</p>")
    assert [s for s, _ in got] == ["BLOCKER"] * 3


# Legitimate text the reviewer found reported as a BLOCKER (30 Sep 2026).
LEGITIMATE = {
    "caption words in prose": "<p>Figure: see below</p>",
    "caption words in a cell": "<table><tr><td>Table: users</td></tr></table>",
    "RFC 6570 template mid-sentence": "<p>The template {#path} expands a fragment (RFC 6570).</p>",
    "RFC 6570 template ending a block": "<p>Expand it as https://example.org/files{#path}</p>",
    "RFC 6570 relative template ending a block": "<p>The fragment form is /files{#path}</p>",
    "Handlebars block helper": "<p>{{#each}}</p><p>Loop with {{#each items}}</p>",
    "a '{{#' opener never counts": "<p>A Mustache section opens as {{#name}</p>",
    "kbd": "<p>Type <kbd>Table: x{#id}</kbd></p>",
    "samp": "<p>It prints <samp>{#id}</samp></p>",
    "var": "<p>Where <var>{#id}</var></p>",
}


@pytest.mark.parametrize("html", LEGITIMATE.values(), ids=LEGITIMATE.keys())
def test_legitimate_text_passes(html):
    assert residue(html) == []


def test_the_five_csaf_csd03_leaks_are_still_caught():
    html = "".join(f"<p>{t}</p>" for t in (
        "Table: Requirements for combinations of <code>category</code> and <code>title</code> "
        "that have a special meaning.{#document-property-notes-tab-1}",
        "Table: Combinations of <code>category</code> and <code>title</code> with special "
        "meaning.{#vulnerabilities-property-notes-tab-1}",
        "Table: Remediation Combinations{#vulnerabilities-property-remediations-category-tab-1}",
        "Table: Product Status Remediation Category Combinations"
        "{#vulnerabilities-property-remediations-category-tab-2}",
        "Table: Comparison of values for <code>$.document.distribution.tlp.label</code> across "
        "CSAF versions 2.0 and 2.1.{#tab:tlp-labels-across-csaf-versions}"))
    got = residue(html)
    assert len(got) == 5 and "'Table: Remediation Combinations{#vulnerabilities" in got[2][1]
    assert "<code>" not in got[4][1] and "$.document.distribution.tlp.label" in got[4][1]


def test_code_numbered_captions_and_ordinary_braces_pass():
    html = ("<pre><code>Table: not a caption {#id}</code></pre>"
            "<p>Use <code>{#id}</code> in pandoc.</p>"
            "<p>Table 1: Remediation Combinations</p>"
            "<p>The set {a, b} and a JSON object {\"k\": 1}.</p>")
    assert residue(html) == []
