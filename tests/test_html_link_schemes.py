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
