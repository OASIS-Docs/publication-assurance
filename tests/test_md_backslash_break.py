# Copyright 2026 OASIS Open
# SPDX-License-Identifier: Apache-2.0
# Authored by Michael Coletta, Technical Advisor to OASIS Open.
"""md-links: the '.\\' rule blocks only a bare URL that pandoc would swallow.

A line ending in a URL then '.\\' (a period, then a backslash hard line break)
is a real defect when the URL is bare: pandoc's autolink_bare_uris reader
pulls the period and the backslash into the href and the line break is lost.
The rule matched any URL, so it also blocked an angle-bracket autolink,
'Schema: <https://.../aggregator.json>.\\', which pandoc renders correctly,
and a link target, '[x](https://...).\\'. Both were found reviewing the
v1.13.1 advice to write dual links as <https://...> (Oct 2026): following
that advice at the end of a line drew a BLOCKER.

Each case below was rendered with pandoc 3.8.2.1,
-f markdown+autolink_bare_uris-implicit_figures, before it was written down.
"""

from __future__ import annotations

import pytest

from conftest import oasis_pub_check


def backslash_blockers(md: str) -> list[str]:
    f = oasis_pub_check.Findings()
    oasis_pub_check.check_md_links(md, f)
    return [x["message"] for x in f.items
            if x["check"] == "md-links" and x["severity"] == "BLOCKER"]


@pytest.mark.parametrize("line", [
    # href="https://example.org/x/aggregator.json.\", line break lost
    "Schema: https://example.org/x/aggregator.json.\\",
    # a closing parenthesis inside a bare URL does not end it:
    # href="https://en.wikipedia.org/wiki/Foo_(bar).\"
    "See https://en.wikipedia.org/wiki/Foo_(bar).\\",
    # the second URL is bare even though the first is a link target
    "See [x](https://example.org/a)https://example.org/b.\\",
    # a bare URL after an angle-bracket autolink on the same line
    "See <https://example.org/a> and https://example.org/b.\\",
    # An opening '<' or '(' that is never closed before '.\\' does not end the
    # URL either. The first version of this fix exempted any URL after '<' or
    # '(' and missed all of these; the adversarial review found them.
    "a<https://x.org/y.\\",
    "(https://x.org/y.\\",
    "f(https://x.org/y.\\",
    "[t](https://x.org/y.\\",
    "x(https://a.org/b) and (https://x.org/y.\\",
    # href="https://x.org/Foo_(bar).\\": the inner pair closes, the outer does not
    "(https://x.org/Foo_(bar).\\",
])
def test_a_bare_url_running_into_a_backslash_break_still_blocks(line):
    got = backslash_blockers(line + "\nnext line\n")
    assert len(got) == 1, got
    assert "Line 1:" in got[0], got[0]


@pytest.mark.parametrize("line", [
    # href="https://example.org/x/aggregator.json", then '.' and <br />
    "Schema: <https://example.org/x/aggregator.json>.\\",
    # href="https://example.org/x/aggregator.json", then '.' and <br />
    "See [x](https://example.org/x/aggregator.json).\\",
    # pandoc ends a bare URL before a closing parenthesis it did not open
    "See (https://example.org/x.json).\\",
    # href="https://x.org/Foo_(bar)", then '.' and <br />
    "(https://x.org/Foo_(bar)).\\",
])
def test_a_url_closed_before_the_period_does_not_block(line):
    assert backslash_blockers(line + "\nnext line\n") == []
