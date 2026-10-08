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


# Round two: code, raw HTML and math that pandoc renders without a link, and
# the indented lines in those places that are still prose. Each rendered with
# pandoc 3.8.2.1.
U = "https://x.org/y.\\"


@pytest.mark.parametrize("md", [
    # <blockquote><pre><code>: inside a quote, '>' and one space come off
    # first, then four spaces make code
    f"> q\n>\n>     {U}\n",
    f"> > q\n> >\n> >     {U}\n",
    # in a list item, code starts four spaces past the item's text column
    f"- item\n\n      {U}\n",
    f"1. item\n\n       {U}\n",
    f"-   item\n\n        {U}\n",
    f"- item\n\n  - sub\n\n        {U}\n",
    f"- item\n\n  - sub\n\n  back\n\n      {U}\n",
    # a line indented less than a wide marker's text column ends the list,
    # and four spaces at the top level are code
    f"10.  item\n\n    {U}\n",
    # a footnote or definition takes its text four spaces in, code eight
    f"Text[^1].\n\n[^1]: Note.\n\n        {U}\n",
    f"Term\n:   def\n\n        {U}\n",
    # an indented line straight after a heading is code
    f"# H\n    {U}\n",
    f"H\n=\n    {U}\n",
    f"H\n---\n    {U}\n",
    # raw HTML: a comment, <pre> and <script> pass through untouched
    f"<!--\n{U}\n-->\n",
    f"Text <!-- see {U}\n--> more\n",
    f"<pre>\n{U}\n</pre>\n",
    f"Text <pre>{U}\n</pre>\n",
    f"<script>\n{U}\n</script>\n",
    # a quote's first line starts a block, even straight after code
    f"    code\n>     {U}\n",
    # a <div> line ends a paragraph, so the indented line is code
    f"Text\n<div>\n    {U}\n",
    # a quote indented less than the item's text ends the list
    f"-   item\n\n    para\n\n   > q\n\n    see {U}\n",
    # 'A.' with one space is not a list marker, so this is top-level code
    f"A. Smith\n\n    {U}\n",
    # display math: <span class="math display">, no link
    f"$$\n{U}\n$$\n",
])
def test_a_url_in_code_raw_html_or_math_does_not_block(md):
    assert backslash_blockers(md + "next line\n") == []


@pytest.mark.parametrize("md, line", [
    # '>' and one space, then three: a paragraph, href="https://x.org/y.\\"
    (f"> q\n>\n>    {U}\n", "Line 3"),
    # a tab after '>' reaches only column 4
    (f"> q\n>\n>\t{U}\n", "Line 3"),
    # no blank line inside the quote: the paragraph continues
    (f"> q\n>     {U}\n", "Line 2"),
    # short of the item's text column plus four: a further paragraph
    (f"- item\n\n     {U}\n", "Line 3"),
    (f"1. item\n\n      {U}\n", "Line 3"),
    (f"-   item\n\n    {U}\n", "Line 3"),
    (f"- item\n\n  - sub\n\n      {U}\n", "Line 5"),
    # a heading two lines up does not make the line code
    (f"# H\n\npara\n    {U}\n", "Line 4"),
    # text after a closed comment, a <div>, and a '$' that opens no math
    (f"<!-- a --> {U}\n", "Line 1"),
    (f"<div>\n{U}\n</div>\n", "Line 2"),
    (f"Text $ {U}\n", "Line 1"),
    # '$3' cannot close math, so '$5 ...' is not math
    (f"Cost $5 see {U}\nfor $3\n", "Line 1"),
    # YAML metadata: an abstract's block scalar is Markdown, and the
    # template renders it with href="https://x.org/y.\\"
    (f"---\ntitle: x\nabstract: |\n  a\n\n    {U}\n---\n", "Line 6"),
])
def test_an_indented_or_raw_looking_url_that_pandoc_links_still_blocks(md, line):
    assert backslash_blocker_lines(md + "next line\n") == [line]


# Found by the adversarial review of round two: each blocked before this
# change, and the first version of it hid the defect.
@pytest.mark.parametrize("md, line", [
    # a comment line does not end a paragraph: the indented line continues it
    (f"para\n<!-- note -->\n    {U}\nmore\n", "Line 3"),
    # an indented '#' or underline is not a heading
    (f" # H\n    {U}\n", "Line 2"),
    (f"H\n  ===\n    {U}\n", "Line 3"),
    # a line with an underline below it is a heading, href="https://x.org/y.\\"
    (f"> q\n>\n>     {U}\n---\n", "Line 3"),
    (f"para\n\n    {U}\n---\n", "Line 3"),
    # a quote cannot interrupt a paragraph: all three lines are one paragraph
    (f"Para.\n>\n>     see {U}\n", "Line 3"),
    # after an empty '>' line, an unquoted line continues the quote
    (f"> q\n>\n    see {U}\n", "Line 3"),
    # a quote at the item's text column stays in the item, and so does the
    # text after it
    (f"1. item\n\n   para\n\n   > q\n\n    see {U}\n", "Line 7"),
    # an unquoted line after a quoted comment continues the quote
    (f"> <!-- -->\n    {U}\n", "Line 2"),
    # pandoc reads '$...$' inside each list item and code span, so a '$' in
    # the next item or in code does not close math around the URL
    (f"- Basic: $5 {U}\n- Pro: US$ 10\n", "Line 1"),
    (f"Set ``$HOME`` and see {U}\nthen ``$PATH`` too\n", "Line 1"),
    # an escaped '<', a comment closed at once, a self-closing <pre/>
    (f"\\<!-- {U}\n-->\n", "Line 1"),
    (f"<!--> {U}\n-->\n", "Line 1"),
    (f"<pre/>\n{U}\n</pre>\n", "Line 2"),
])
def test_round_two_review_counterexamples_still_block(md, line):
    assert backslash_blocker_lines(md + "next line\n") == [line]


# Round three, each rendered with pandoc 3.8.2.1. A block-level HTML tag
# alone on its line (other than <div>) opens pandoc's raw HTML block: the
# next line may open a quote, and every block inside gives up as many spaces
# as the line after the tag is indented, so a whitespace-only line there
# stops four-space code. A fence needs its closing line; inside a list item
# or a quote it is code as at the top level.
@pytest.mark.parametrize("md", [
    # <pre>, then <blockquote><pre><code>
    f"<pre>\n>     {U}\n",
    f"<section>\n>     {U}\n",
    # an empty line after the tag leaves four spaces for code
    f"<pre>\n\n    {U}\n",
    f"<section>\n \n</section>\n\n    {U}\n",
    # <div> gives up no spaces
    f"<div>\n \n    {U}\n",
    # fenced code inside a list item or a quote: <pre><code>
    f"- item\n\n  ```\n  {U}\n  ```\n",
    f"1. item\n\n   ~~~\n   {U}\n   ~~~\n",
    f"- item\n  ```\n  {U}\n  ```\n",
    f"- item\n\n    ```\n    {U}\n    ```\n",
    f"- item\n\n  ```\n  x\n\n  {U}\n  ```\n",
    f"- item\n\n  ````\n  ```\n  {U}\n  ````\n",
    f"- item\n\n  ```\n{U}\n  ```\n",
    f"> q\n>\n> ```\n> {U}\n> ```\n",
    f"> ```\n{U}\n> ```\n",
    # '- x' straight after a paragraph line is not a list item (pandoc reads
    # 'Para - x'), so four spaces after the blank line are top-level code
    f"Para\n- x\n\n    {U}\n",
    # a fence indented one to three spaces at the top level
    f"  ```\n  {U}\n  ```\n",
])
def test_round_three_code_does_not_block(md):
    assert backslash_blockers(md + "next line\n") == []


@pytest.mark.parametrize("md, line", [
    # the whitespace-only line sets the spaces given up: href="https://x.org/y.\\"
    (f"<pre>\n \n    {U}\n", "Line 3"),
    (f"<pre>\n\t\n    {U}\n", "Line 3"),
    (f"<section>\n \n    {U}\n", "Line 3"),
    (f"<pre>\n \n\n    {U}\n", "Line 4"),
    (f"<pre>\n \nx\n\n    {U}\n", "Line 5"),
    (f"<ul>\n<li>\n \n    {U}\n", "Line 4"),
    # text after the tag: the next line continues that paragraph
    (f"<pre> x\n>     {U}\n", "Line 2"),
    # a fence indented past the item's text cannot interrupt its paragraph:
    # '~~~' is text, href="https://x.org/y.\\"
    (f"- item\n   ~~~\n   {U}\n   ~~~\n", "Line 3"),
    # a fence with no closing line is text
    (f"- item\n\n  ```\n  {U}\n", "Line 4"),
])
def test_round_three_near_misses_still_block(md, line):
    assert backslash_blocker_lines(md + "next line\n") == [line]


def test_crlf_never_reaches_the_rule(tmp_path):
    # pub-check reads the Markdown with read_text, in text mode, so '\r\n'
    # arrives as '\n'. pandoc reads the same file the same way:
    # <pre><code>https://x.org/a.\\</code></pre>, then href="https://x.org/b.\\"
    p = tmp_path / "crlf.md"
    p.write_bytes(b"Para.\r\n\r\n    https://x.org/a.\\\r\n\r\nSee https://x.org/b.\\\r\nnext\r\n")
    text = oasis_pub_check.read_text(str(p))
    assert "\r" not in text
    assert backslash_blocker_lines(text) == ["Line 5"]


# Found by the adversarial review of round three: the first version of it
# hid each of these defects (pandoc links the URL) or blocked real code.
@pytest.mark.parametrize("md, line", [
    # a list opens after a table row, a close tag or code, so six spaces
    # after its blank line are the item's paragraph, not code
    (f"| a |\n|---|\n| b |\n1.  item\n\n      see {U}\n", "Line 6"),
    (f"</section>\n-   item\n\n      see {U}\n", "Line 4"),
    (f"Para.\n\n    code\n1.  item\n\n      see {U}\n", "Line 6"),
    # '~~~' at the item's text column, after its text, is text
    (f"- item\n  ~~~\n  see {U}\n  ~~~\n", "Line 3"),
    (f"> para\n> ~~~\n> see {U}\n> ~~~\n", "Line 3"),
    # a backtick in a tilde fence's info string makes it text
    (f"- item\n\n  ~~~ a`b\n  see {U}\n  ~~~\n", "Line 4"),
    # a fence whose closing line comes after its item has ended is text
    (f"- item\n\n  ```\n  see {U}\n\nPara\n\n```\n", "Line 4"),
    # inside a multiline table a fence line is a cell's text
    (f"---\n2) x\n  ```\n  see {U}\n  ```\n(1) x\n---\n\n", "Line 4"),
    # a tag line continuing a quote's paragraph opens nothing
    (f"> q\n<section>\n>     see {U}\n", "Line 3"),
])
def test_round_three_review_counterexamples_still_block(md, line):
    assert backslash_blocker_lines(md + "next line\n") == [line]


@pytest.mark.parametrize("md", [
    # the spaces a tag's blocks give up are counted past the item's text
    f"- item\n\n  <section>\n  text\n\n      code {U}\n",
    # a nested tag is recognised past the enclosing block's indent
    f"<table>\n  <tr>\n    <td>\n\n      code {U}\n    </td>\n  </tr>\n</table>\n",
    # the indent a tag's blocks give up does not reach into a quote
    f"<section>\n \n\n>     {U}\n",
])
def test_round_three_review_code_does_not_block(md):
    assert backslash_blockers(md + "next line\n") == []
