# Copyright 2026 OASIS Open
# SPDX-License-Identifier: Apache-2.0
# Authored by Michael Coletta, Technical Advisor to OASIS Open.
"""html-anchors: a link whose href is a cross-reference id without its '#'.

CSAF v2.1 csd03 (Sep 2026) publishes <a href="tab:tlp-labels-across-csaf-versions">,
a pandoc-crossref reference no filter resolved. A browser reads 'tab:' as a
URL scheme and the link goes nowhere. The anchor check read only '#' links,
so nothing reported it. Same failure as an unresolved fragment, so the same
severity: BLOCKER on the markdown track, WARN on DOCX-native.
"""

from __future__ import annotations

import pytest

from conftest import oasis_pub_check

GOOD = ('<p><a href="#s1">1</a> <a href="https://example.org/">w</a> '
        '<a href="mailto:a@b.c">m</a> <a href="urn:ietf:rfc:2119">u</a> '
        '<a href="schema/csaf.json">r</a> <a href="../csd02/x.html#y">p</a> '
        '<a href="data:text/plain,hi">d</a></p><h1 id="s1">1</h1>')


def scheme_findings(html, severity=oasis_pub_check.BLOCKER):
    f = oasis_pub_check.Findings()
    oasis_pub_check.check_html("<title>Widget Version 1.0</title>" + html, "wid-v1.0-csd01", f,
                               anchor_severity=severity)
    return [(x["severity"], x["message"]) for x in f.items
            if x["check"] == "html-anchors" and "is not a web URL scheme" in x["message"]]


def test_a_cross_reference_without_its_hash_blocks():
    got = scheme_findings(GOOD + '<p>see <a href="tab:tlp-labels">tab</a></p>')
    assert [s for s, _ in got] == ["BLOCKER"] and "'tab:tlp-labels'" in got[0][1]


def test_the_hint_names_the_anchor_when_the_document_has_it():
    got = scheme_findings(GOOD + '<table id="tlp-labels"></table><a href="tab:tlp-labels">t</a>')
    assert "write href=\"#tlp-labels\"" in got[0][1]


def test_web_schemes_fragments_and_relative_links_pass():
    assert scheme_findings(GOOD) == []


def test_docx_native_track_warns():
    got = scheme_findings(GOOD + '<a href="fig:one">f</a>', severity=oasis_pub_check.WARN)
    assert [s for s, _ in got] == ["WARN"]


# Registered non-web identifiers and ordinary links a specification uses.
# The reviewer (30 Sep 2026) found did:, isbn:, hdl:, ark:, cpe: and x-foo:
# reported as BLOCKERs under the old list-of-web-schemes rule.
PASSING = ["tel:+15555550100", "doi:10.1000/182", "javascript:void(0)", "MAILTO:a@b.c",
           "did:example:123456789abcdefghi", "isbn:9780141036144", "hdl:20.1000/100",
           "ark:12025/654xz321", "cpe:2.3:a:vendor:product:1.0", "x-foo:bar",
           "urn:oasis:names:tc:csaf", "ns:element.html"]


@pytest.mark.parametrize("href", PASSING)
def test_registered_schemes_and_relative_paths_pass(href):
    assert scheme_findings(GOOD + f'<a href="{href}">x</a>') == []


@pytest.mark.parametrize("href", ["tab:x#y", "tab:x?y", "tbl:users", "fig:one", "sec:intro",
                                  "eq:energy", "lst:code", "TAB:upper"])
def test_every_crossref_prefix_blocks_whatever_follows(href):
    got = scheme_findings(GOOD + f'<a href="{href}">x</a>')
    assert [s for s, _ in got] == ["BLOCKER"], href


def test_any_prefix_blocks_when_the_document_has_that_id():
    got = scheme_findings(GOOD + '<h2 id="ns:element.html">E</h2><a href="ns:element.html">e</a>')
    assert [s for s, _ in got] == ["BLOCKER"] and "write href=\"#ns:element.html\"" in got[0][1]


def test_a_target_whose_id_leaked_as_text_is_named():
    got = scheme_findings(GOOD + '<p>Table: Labels{#tab:labels}</p><a href="tab:labels">t</a>')
    assert len(got) == 1 and "'{#tab:labels}' is printed as text" in got[0][1]
