# Copyright 2026 OASIS Open
# SPDX-License-Identifier: Apache-2.0
# Authored by Michael Coletta, Technical Advisor to OASIS Open.
"""residue: the 'Will be filled in' template placeholder, not the phrase.

The check matched "will be filled in" anywhere, so KMIP Test Cases v3.0 WD01
s2 drew a placeholder WARN for a sentence of specification prose (14 Oct
2026). The template's placeholder, as OpenEoX EoX Core v1.0 csd01 published
it, still warns in both its Markdown and its HTML form.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from conftest import oasis_pub_check

WARNING = "'Will be filled in …' placeholder present"


def fill_in(md="", html=""):
    f = oasis_pub_check.Findings()
    oasis_pub_check.check_residue(md, html, f)
    return [(x["severity"], x["message"]) for x in f.items
            if x["check"] == "residue" and WARNING in x["message"]]


PROSE = {
    # The KMIP Word HTML, as staged, wrapped where Word wrapped it.
    "KMIP html": ('\t<p class="western"><font>dynamic items are indicated using symbolic '
                  'identifiers – in actual\n\trequest and response messages these '
                  'dynamic values will be filled in\n\twith valid values.</font></p>'),
    "KMIP markdown": ("In actual request and response messages these dynamic values "
                      "will be filled in with valid values."),
    "wrapped before the phrase": "These dynamic values\nwill be filled in with valid values.",
    "in a list item": "- the identifiers will be filled in by the server",
}


@pytest.mark.parametrize("text", PROSE.values(), ids=PROSE.keys())
def test_the_phrase_in_prose_does_not_warn(text):
    assert fill_in(md=text, html=text) == []


PLACEHOLDERS = {
    "EoX markdown": ("markdown", "- \\< Will be filled in at CS01 \\>"),
    "EoX html": ("html", "<ul>\n      <li>&lt; Will be filled in at CS01 &gt;\n      </li>\n    </ul>"),
    "bare angle brackets": ("markdown", "< will be filled in by the TC Admin >"),
    "square brackets": ("markdown", "[Will be filled in]"),
    "a line of its own": ("markdown", "Will be filled in at CS01"),
    "a list item": ("markdown", "* Will be filled in"),
    "a table cell": ("markdown", "| Editor | Will be filled in |"),
    "an element": ("html", "<td>Will be filled in</td>"),
}


@pytest.mark.parametrize("where,text", PLACEHOLDERS.values(), ids=PLACEHOLDERS.keys())
def test_the_template_placeholder_still_warns(where, text):
    got = fill_in(**{"md" if where == "markdown" else "html": text})
    assert [s for s, _ in got] == ["WARN"]
    assert f"present in {where}" in got[0][1]


# Counterexamples from the adversarial review (14 Oct 2026): forms a DOCX-native
# spec's Word HTML or an editor could leave, missed by the first draft.
def test_word_html_entities_and_nbsp_still_warn():
    for html in ("<p>&lt;&nbsp;Will be filled in&gt;</p>", "<li>&nbsp;Will be filled in</li>",
                 "<li>\xa0Will be filled in</li>", "<p>&#60; Will be filled in &#62;</p>",
                 "<p>&#x3C;Will be filled in&#x3E;</p>"):
        assert [s for s, _ in fill_in(html=html)] == ["WARN"], html


def test_a_parenthesised_numbered_or_emphasised_placeholder_still_warns():
    for md in ("- (Will be filled in at CS01)", "1. Will be filled in", "*Will be filled in*",
               "- **Will be filled in at CS01**"):
        assert [s for s, _ in fill_in(md=md)] == ["WARN"], md


def test_filled_independently_is_not_the_placeholder():
    # ODF v1.4 part 3 prose; "filled in" is only the start of "filled independently".
    for text in ("The areas will be filled independently of each other.",
                 "- Will be filled independently", "[will be filled into the table]"):
        assert fill_in(md=text, html=text) == [], text


def test_the_nide_rule_uses_the_same_expression():
    rules = yaml.safe_load((Path(oasis_pub_check.__file__).parent / "rules" /
                            "oasis.rules.yaml").read_text(encoding="utf-8"))
    rule = next(r for r in rules["rules"] if r["id"] == "OASIS-RESID-FILL-IN")
    assert rule["check"]["pattern"] == oasis_pub_check.FILL_IN_PLACEHOLDER_RE.pattern
    assert "flags" not in rule["check"]
