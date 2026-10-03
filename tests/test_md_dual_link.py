# Copyright 2026 OASIS Open
# SPDX-License-Identifier: Apache-2.0
# Authored by Michael Coletta, Technical Advisor to OASIS Open.
"""md-links: a dual link [url](url) is fixed with <url>, not a bare URL.

The warning used to say "prefer a bare URL (autolinked)". A bare URL is not a
link in the PDF, so an editor following that advice lost the link. The CSAF
editor asked whether <url> was better (oasis-tcs/csaf PR #1635, Oct 2026); it
is, and it is the form the check already accepts. The message now says so.
"""

from __future__ import annotations

from conftest import oasis_pub_check

URL = "https://docs.oasis-open.org/csaf/csaf/v2.1/csaf-v2.1.html"


def md_links_warnings(md: str) -> list[str]:
    f = oasis_pub_check.Findings()
    oasis_pub_check.check_md_links(md, f)
    return [x["message"] for x in f.items
            if x["check"] == "md-links" and x["message"].startswith("Dual link")]


def test_a_dual_link_warns_and_recommends_the_angle_bracket_autolink():
    got = md_links_warnings(f"See [{URL}]({URL}) for details.\n")
    assert len(got) == 1, got
    assert "<https://...>" in got[0], got[0]
    assert "both the HTML and the PDF" in got[0], got[0]
    assert "bare URL" not in got[0], got[0]
    assert got[0].endswith(URL), got[0]


def test_an_angle_bracket_autolink_does_not_warn():
    assert md_links_warnings(f"See <{URL}> for details.\n") == []


def test_a_link_with_real_anchor_text_does_not_warn():
    assert md_links_warnings(f"See [the CSAF specification]({URL}).\n") == []
