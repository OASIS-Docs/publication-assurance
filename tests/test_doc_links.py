# Copyright 2026 OASIS Open
# SPDX-License-Identifier: Apache-2.0
# Authored by Michael Coletta, Technical Advisor to OASIS Open.
"""Every relative link in the documentation must point at a file that exists.

The DocBook action told its readers to "See docs/MARKDOWN-FROM-DOCBOOK.md", a
file that never existed, and the guide it meant had been renamed once already
(CONVERTING.md became CONVERT-AND-VERIFY.md). Nothing read the links, so
nothing noticed. This reads every relative Markdown link in the guides and
READMEs, and every `docs/*.md` path a workflow or action file names.

Anchors (`#section`) are not checked: GitHub derives them from headings, and a
stale anchor still lands the reader on the right page.
"""

from __future__ import annotations

import re
import subprocess

import pytest

from conftest import REPO_ROOT

LINK = re.compile(r"\]\(([^)\s]+)\)")
DOC_PATH = re.compile(r"\bdocs/[A-Za-z0-9._-]+\.md\b")


def _tracked(*patterns):
    out = subprocess.run(["git", "-C", str(REPO_ROOT), "ls-files", *patterns],
                         capture_output=True, text=True, check=True).stdout
    return sorted(out.split())


def _docs():
    # examples/ and tests/fixtures/ hold published specifications and dated
    # reports, kept byte for byte; their links are theirs, not ours.
    return [p for p in _tracked("*.md")
            if not p.startswith(("examples/", "tests/fixtures/", ".github/src/"))]


def _relative_targets(text):
    text = re.sub(r"(?ms)^(```|~~~).*?^\1", "", text)
    text = re.sub(r"`[^`\n]*`", "", text)
    for target in LINK.findall(text):
        if re.match(r"^[a-z][a-z0-9+.-]*:", target) or target.startswith("#"):
            continue
        yield target.split("#", 1)[0].split("?", 1)[0]


@pytest.mark.parametrize("rel", _docs())
def test_every_relative_link_resolves(rel):
    doc = REPO_ROOT / rel
    missing = sorted({t for t in _relative_targets(doc.read_text(encoding="utf-8"))
                      if t and not (doc.parent / t).exists()})
    assert not missing, f"{rel} links to files that do not exist: {missing}"


@pytest.mark.parametrize("rel", _tracked("*.yml", "*.yaml"))
def test_every_guide_a_workflow_names_exists(rel):
    text = (REPO_ROOT / rel).read_text(encoding="utf-8")
    missing = sorted({p for p in DOC_PATH.findall(text) if not (REPO_ROOT / p).exists()})
    assert not missing, f"{rel} names guides that do not exist: {missing}"


def test_the_link_reader_finds_links():
    """A reader that matched nothing would pass every document."""
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert len(list(_relative_targets(readme))) > 10
    assert len(_docs()) > 10
