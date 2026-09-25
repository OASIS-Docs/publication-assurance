# Copyright 2026 OASIS Open
# SPDX-License-Identifier: Apache-2.0
# Authored by Michael Coletta, Technical Advisor to OASIS Open.
"""The adoption guide, the README and the example workflows tell a TC which
release to pin. A pin older than the newest release sends a TC to a gate
without the latest checks; a newer one names a tag that does not exist.
Every pin must name the newest version in CHANGELOG.md, so cutting a
release fails this test until the documentation follows it.

The guide also carries a note that report publishing arrives in the release
after v1.5.0. Once the newest release is past v1.5.0 that note is stale, and
this test says so.
"""
import re

from conftest import REPO_ROOT

PINNED = ["docs/ADOPTING.md", "README.md", "examples/consumer-workflow.yml",
          "examples/consumer-workflow-matrix.yml", "action.yml"]
PIN = re.compile(r"publication-assurance@(v\d+\.\d+\.\d+)|--branch (v\d+\.\d+\.\d+)"
                 r"|PA_REF: (v\d+\.\d+\.\d+)|refs/tags/(v\d+\.\d+\.\d+)|`@(v\d+\.\d+\.\d+)`")
NOTE = "in the release after v1.5.0"


def newest_release() -> str:
    changelog = (REPO_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    return re.search(r"^## (v\d+\.\d+\.\d+) ", changelog, re.M).group(1)


def pins() -> dict[str, set[str]]:
    found = {}
    for rel in PINNED:
        text = (REPO_ROOT / rel).read_text(encoding="utf-8")
        found[rel] = {next(g for g in m.groups() if g) for m in PIN.finditer(text)}
    return found


def test_every_pin_names_the_newest_release():
    newest = newest_release()
    stale = {rel: sorted(v - {newest}) for rel, v in pins().items() if v - {newest}}
    assert not stale, (f"pins that are not the newest release {newest}: {stale}. "
                       "Update them when a release is cut.")


def test_the_pin_patterns_actually_match():
    """A pin check whose pattern matches nothing passes on any document."""
    found = pins()
    assert len(found["docs/ADOPTING.md"]) >= 1 and found["examples/consumer-workflow.yml"]


def test_the_publishing_note_goes_when_publishing_is_released():
    guide = " ".join((REPO_ROOT / "docs/ADOPTING.md").read_text(encoding="utf-8").split())
    if newest_release() != "v1.5.0":
        assert NOTE not in guide, (
            "docs/ADOPTING.md still says report publishing arrives "
            f"'{NOTE}', but the newest release is {newest_release()}: remove the note.")
