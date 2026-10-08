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


# The gaps PR #63 left, each rendered with pandoc 3.8.2.1 the same way.
# pandoc's bare-URI reader (Text.Pandoc.Parsing.General.uri) takes any scheme
# on its list (src/Text/Pandoc/URI.hs), in any letter case, and counts '\\' as
# a URL character, so a URL that runs into the line's closing backslash takes
# it into the href whatever comes just before it.
@pytest.mark.parametrize("line", [
    # href="HTTPS://x.org/y.\\": the scheme matches in any case
    "Schema: HTTPS://x.org/y.\\",
    "Schema: Http://x.org/y.\\",
    # href="ftp://x.org/y.\\", href="mailto:a@x.org.\\"
    "Get it from ftp://x.org/y.\\",
    "Contact mailto:a@x.org.\\",
    # href="urn:oasis:names:tc:x:y.\\": urn is on pandoc's list
    "Namespace: urn:oasis:names:tc:x:y.\\",
    # href="https://x.org/y.\\"; a space after the backslash does not stop it
    "Schema: https://x.org/y.\\ ",
    # an autolink closed after the backslash: href="https://x.org/y.\\"
    "see <https://x.org/y.\\>",
    # an autolink runs on to the '>' even where a bare URL would stop:
    # href="https://x.org/y!.\\"
    "see <https://x.org/y!.\\>",
    # an email autolink: href="mailto:a@x.org.\\"
    "Write to <a@x.org.\\>",
    # no period: href="https://x.org/y\\" and href="https://x.org/y/\\"
    "See https://x.org/y\\",
    "See https://x.org/y/\\",
    # a URL after '_' is still bare: _<a href="https://x.org/y.\\">
    "See _https://x.org/y.\\",
])
def test_any_uri_pandoc_links_running_into_the_backslash_blocks(line):
    got = backslash_blockers(line + "\nnext line\n")
    assert len(got) == 1, got
    assert "Line 1:" in got[0], got[0]


@pytest.mark.parametrize("line", [
    # pandoc ends the URL at a punctuation mark that is not followed by a URL
    # character, so each of these renders <a href="https://x.org/y">, then the
    # text, then '.' and <br />.
    '"https://x.org/y".\\',
    "*https://x.org/y*.\\",
    "**https://x.org/y**.\\",
    "See https://x.org/y!.\\",
    "See https://x.org/(a.b).\\",
    # the URL in the link text and the target both end before ']' or ')'
    "[https://x.org/y](https://x.org/y).\\",
    "[see https://x.org/y](https://x.org/z).\\",
    # not linked at all: pandoc reads 'ahttps' and '.https' as words, and
    # 'ftps' and 'type' are not on its scheme list
    "See ahttps://x.org/y.\\",
    "See x.https://x.org/y.\\",
    "See ftps://x.org/y.\\",
    "Use type:string.\\",
    # pandoc reads no URL when '*', '_' or ']' follows the colon
    "Use notes:_a.\\",
    # a closed link keeps the break with no period: href="https://x.org/y",
    # then <br />; and a URL in brackets ends at the ']'
    "See [x](https://x.org/y)\\",
    "See [https://x.org/y]\\",
    # the fix the message advises: href="https://x.org/y", then '. ' and <br />
    "Schema: https://x.org/y. \\",
])
def test_a_uri_pandoc_ends_before_the_backslash_does_not_block(line):
    assert backslash_blockers(line + "\nnext line\n") == []


def backslash_blocker_lines(md: str) -> list[str]:
    return [m.split(":")[0] for m in backslash_blockers(md)]


@pytest.mark.parametrize("md", [
    # <pre><code>https://x.org/y.\\</code></pre>
    "Para.\n\n    https://x.org/y.\\\n",
    "Para.\n\n\thttps://x.org/y.\\\n",
    # a code block that runs on past a blank line stays one code block
    "Para.\n\n    code\n\n    https://x.org/y.\\\n",
    # a paragraph after a list ends the list, so the indented line is code
    "- item\n\nPara.\n\n    https://x.org/y.\\\n",
])
def test_a_url_in_an_indented_code_block_does_not_block(md):
    assert backslash_blockers(md + "next line\n") == []


@pytest.mark.parametrize("md, line", [
    # inside a list item a four-space indent continues the item: pandoc
    # renders <p><a href="https://x.org/y.\\">, not a code block
    ("- item\n\n    https://x.org/y.\\\n", "Line 3"),
    ("1. item\n\n    https://x.org/y.\\\n", "Line 3"),
    ("- item\n- item2\n\n    https://x.org/y.\\\n", "Line 4"),
    # likewise a footnote and a definition continue at four spaces
    ("Text[^1].\n\n[^1]: Note.\n\n    https://x.org/y.\\\n", "Line 5"),
    ("Term\n:   def\n\n    https://x.org/y.\\\n", "Line 4"),
    # an indented line with no blank line before it continues the paragraph
    ("Para\n    https://x.org/y.\\\n", "Line 2"),
])
def test_an_indented_url_that_is_not_code_still_blocks(md, line):
    assert backslash_blocker_lines(md + "next line\n") == [line]


# Found by the adversarial review of this change, each rendered with pandoc.
@pytest.mark.parametrize("md, line", [
    # a no-break space is not a blank line: the indented line continues
    # the paragraph, href="https://x.org/y.\\"
    ("Para.\n\u00a0\n    https://x.org/y.\\\n", "Line 3"),
    # a list marker alone on its line still opens the item
    ("1.\n    item\n\n    https://x.org/y.\\\n", "Line 4"),
    # a footnote may be indented up to three spaces
    ("Text[^1].\n\n [^1]: Note.\n\n    https://x.org/y.\\\n", "Line 5"),
    # a multiline table's row is not code however far it is indented
    ("-------------------------------------\n First    row\n\n"
     "    Second  https://x.org/y.\\\n            next\n"
     "-------------------------------------\n", "Line 4"),
    # an escaped '@', '.' or backslash does not stop pandoc starting a URL
    ("See \\@https://x.org/y.\\\n", "Line 1"),
    ("See \\.https://x.org/y.\\\n", "Line 1"),
    ("See \\\\https://x.org/y.\\\n", "Line 1"),
    # an escaped ')' does not close a link target: href="https://x.org/a\\)\\"
    ("See [x](https://x.org/a\\)\\\n", "Line 1"),
    # a grid-table cell ending in a backslash break
    ("+-----------------------+------+\n| https://x.org/y.\\     | b    |\n"
     "| more                  |      |\n+-----------------------+------+\n", "Line 2"),
])
def test_review_counterexamples_that_must_block(md, line):
    assert backslash_blocker_lines(md + "next line\n") == [line]


@pytest.mark.parametrize("line", [
    # pandoc reads one URL, href="https://x.org/go?to=http", then ':.' and
    # <br />; the 'http:' inside it is not a second URL
    "Redirect: https://x.org/go?to=http:.\\",
    # not email autolinks to pandoc: '<a@[1.2.3.4]\\>' is text, and
    # '<"a"@x.org\\>' links only a"@x.org, without the backslash
    "Write to <a@[1.2.3.4]\\>",
    'Write to <"a"@x.org\\>',
])
def test_review_counterexamples_that_must_not_block(line):
    assert backslash_blockers(line + "\nnext line\n") == []
