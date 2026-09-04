"""The shipped markdown must render as prose, not as HTML.

GitHub Flavored Markdown allows inline HTML, so an angle-bracketed token in a
paragraph is not text. `<h1>` opens a real heading: the title-oasis-prefix
description shipped in CHECKS.md with two thirds of its words at heading size,
and `<spec>`, `<name>` and `<meta>` were dropped from the rendered page
entirely, because the sanitizer removes tags it does not recognise. Neither
failure is visible in the source.

Both generators escape angle brackets now. This pins the result at the files a
reader actually opens, which is the only place it matters.
"""

from __future__ import annotations

import re

import pytest

from conftest import REPO_ROOT

# The inline HTML the documentation deliberately uses: the README's centred
# badge block and its collapsible layout section.
DELIBERATE = {"p", "a", "img", "br", "details", "summary"}

DOCS = [
    "README.md",
    "PUBLICATION-QUALITY.md",
    "TRANSFORMS.md",
    "CHANGELOG.md",
    "pub-check/README.md",
    "pub-check/CHECKS.md",
    "pub-check/AUTHORITIES.md",
    "pub-check/rules/README.md",
    "assets/architecture/README.md",
    "examples/eox-core-v1.0-csd01/README.md",
]

TAG = re.compile(r"<(/?)([A-Za-z][A-Za-z0-9]*)\b[^>\n]*>|<([^\s>]+)>")


def prose_only(text: str) -> str:
    """Strip what markdown already renders literally: comments, fenced code
    blocks, indented code blocks, and inline code spans."""
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    text = re.sub(r"^```.*?^```", "", text, flags=re.S | re.M)
    text = re.sub(r"`[^`\n]*`", "", text)
    return "\n".join(ln for ln in text.splitlines() if not ln.startswith("    "))


def stray_tags(text: str) -> list[str]:
    found = []
    for m in TAG.finditer(prose_only(text)):
        name = (m.group(2) or m.group(3) or "").lower()
        if name.split("/")[-1] not in DELIBERATE:
            found.append(m.group(0))
    return found


LINK = re.compile(r"!?\[[^\]]*\]\(([^)\s]+)\)")


def relative_links(text: str):
    """Every markdown link and image target that points inside the repository."""
    for m in LINK.finditer(prose_only(text)):
        target = m.group(1)
        if target.startswith(("http://", "https://", "mailto:", "#")):
            continue
        yield m.group(0), target.split("#")[0].split("?")[0]


@pytest.mark.parametrize("rel", DOCS)
def test_every_relative_link_resolves(rel):
    """Bracket-paren syntax in a sentence is a link, not an illustration.
    The catalog described the dual-link check as "No dual [url](url) links"
    and shipped two dead links per row for it."""
    doc = REPO_ROOT / rel
    broken = [whole for whole, target in relative_links(doc.read_text(encoding="utf-8"))
              if target and not (doc.parent / target).resolve().exists()]
    assert not broken, (
        f"{rel} carries link syntax whose target does not exist: {sorted(set(broken))}. "
        f"If it is an illustration of link syntax rather than a link, put it in backticks.")


@pytest.mark.parametrize("rel", DOCS)
def test_no_unescaped_html_in_prose(rel):
    stray = stray_tags((REPO_ROOT / rel).read_text(encoding="utf-8"))
    assert not stray, (
        f"{rel} carries angle-bracketed text outside a code span: "
        f"{sorted(set(stray))}. GitHub parses these as HTML: a known tag "
        f"renders as an element, an unknown one is deleted from the page. "
        f"Escape them (&lt;h1&gt;) or wrap them in backticks.")


def test_the_detector_catches_a_raw_tag():
    """A check that cannot fail is not a check."""
    assert stray_tags("a bare <h1> in a paragraph") == ["<h1>"]
    assert stray_tags("a placeholder <spec>-<stage> name") == ["<spec>", "<stage>"]
    assert stray_tags("an escaped &lt;h1&gt; and a coded `<h1>`") == []


def test_the_link_detector_catches_a_dead_target():
    assert [w for w, tgt in relative_links("see [it](nope/missing.md) here")] == \
        ["[it](nope/missing.md)"]
    assert list(relative_links("a coded `[url](url)` example")) == []
