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


def test_caption_syntax_alone_and_attribute_syntax_alone_each_block():
    assert len(residue("<p>Figure: The widget</p><p>Some text{#anchor-1}</p>")) == 2


def test_code_numbered_captions_and_ordinary_braces_pass():
    html = ("<pre><code>Table: not a caption {#id}</code></pre>"
            "<p>Use <code>{#id}</code> in pandoc.</p>"
            "<p>Table 1: Remediation Combinations</p>"
            "<p>The set {a, b} and a JSON object {\"k\": 1}.</p>")
    assert residue(html) == []
