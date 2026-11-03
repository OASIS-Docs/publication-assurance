# Copyright 2026 OASIS Open
# SPDX-License-Identifier: Apache-2.0
# Authored by Michael Coletta, Technical Advisor to OASIS Open.
"""The wiki is generated from the repository's markdown on every push to main.

The workflow that publishes it only runs from main, so a pull request never
exercises it. This test runs the generator itself and checks what a reader of
the wiki would follow:

- every link in the sidebar names a page the generator wrote, and every
  page the generator wrote is in the sidebar (set equality, not a sample);
- no relative link survives into the output: each one became a wiki page
  name or an absolute URL;
- every github.com blob or tree URL names a path that exists;
- every #anchor on a link to another wiki page matches a heading on it.
"""
from __future__ import annotations

import importlib.util
import re

import pytest

from conftest import REPO_ROOT

_spec = importlib.util.spec_from_file_location(
    "build_wiki", REPO_ROOT / ".github" / "scripts" / "build_wiki.py")
build_wiki = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(build_wiki)

REPO = "OASIS-Docs/publication-assurance"
LINK = re.compile(r"\]\(([^)\s]+)\)")
ATTR = re.compile(r"""\b(?:href|src)=["']([^"']+)["']""")
SCHEME = re.compile(r"^[a-z][a-z0-9+.-]*:", re.I)
BLOB = re.compile(rf"^https://github\.com/{REPO}/(?:blob|tree)/main/([^?#]+)")


def _strip_code(text):
    text = re.sub(r"(?ms)^[ \t]*(`{3,}|~{3,})(?!`)[^`\n]*\n.*?^[ \t]*\1[ \t]*$", "", text)
    return re.sub(r"`[^`\n]*`", "", text)


def _targets(text):
    text = _strip_code(text)
    return LINK.findall(text) + ATTR.findall(text)


def _slug(heading):
    # GitHub's heading anchors: lowercase, drop punctuation, spaces to hyphens.
    s = re.sub(r"[`*]", "", heading.strip().lower())
    s = re.sub(r"[^\w\- ]", "", s)
    return s.replace(" ", "-")


@pytest.fixture(scope="module")
def wiki(tmp_path_factory):
    out = tmp_path_factory.mktemp("wiki")
    written = build_wiki.WikiBuilder(REPO_ROOT, REPO, "main").build(out)
    return {name[:-3]: (out / name).read_text(encoding="utf-8") for name in written}


def test_every_source_is_written(wiki):
    assert set(wiki) == set(build_wiki.PAGES.values())
    assert len(wiki) > 15


def test_sidebar_and_pages_agree(wiki):
    linked = {t.split("#")[0] for t in _targets(wiki["_Sidebar"]) if not SCHEME.match(t)}
    pages = set(wiki) - {"_Sidebar", "_Footer"}
    assert linked == pages, (f"in the sidebar but not generated: {sorted(linked - pages)}; "
                             f"generated but not in the sidebar: {sorted(pages - linked)}")


def test_no_relative_link_survives(wiki):
    bad = {}
    for name, text in wiki.items():
        for t in _targets(text):
            if SCHEME.match(t) or t.startswith("#"):
                continue
            if t.split("#")[0] not in wiki:
                bad.setdefault(name, []).append(t)
    assert not bad, f"links that are neither a wiki page nor an absolute URL: {bad}"


def test_every_blob_url_names_a_real_path(wiki):
    missing = sorted({m.group(1) for text in wiki.values() for t in _targets(text)
                      if (m := BLOB.match(t)) and not (REPO_ROOT / m.group(1)).exists()})
    assert not missing, f"blob or tree URLs to paths that do not exist: {missing}"


def test_anchors_on_wiki_links_match_a_heading(wiki):
    slugs = {name: {_slug(h) for h in re.findall(r"(?m)^#{1,6} (.+)$", _strip_code(text))}
             for name, text in wiki.items()}
    bad = sorted({t for text in (wiki["_Sidebar"], wiki["Home"]) for t in _targets(text)
                  if "#" in t and not SCHEME.match(t)
                  and t.split("#", 1)[1] not in slugs[t.split("#", 1)[0]]})
    assert not bad, f"sidebar or Home anchors with no matching heading: {bad}"


def test_a_broken_link_stops_the_build(tmp_path):
    """A generator that wrote pages over a broken link would publish it."""
    builder = build_wiki.WikiBuilder(REPO_ROOT, REPO, "main")
    builder.rewrite("README.md", "[gone](docs/NO-SUCH-GUIDE.md)")
    assert builder.broken == ["README.md: docs/NO-SUCH-GUIDE.md"]
