"""Every advertised check count must equal what the tool actually runs.

`--list-checks` asserts the condition registry against the code, so the
registry has never drifted. Nothing asserted the numbers the repository
*advertises* against the registry, and that is where it drifted: stage-uri-live
landed on 31 August and the shipped documentation and diagrams went on saying
169 checks across 57 classes for twelve days while the tool ran 170 across 58.

This pins the invariant at the artifacts a reader actually sees, which is the
only place it matters. It deliberately does not test the generators: one of
them (`assets/build.py`) is a local authoring helper and is not in the
repository at all, so a check that ran it would be untestable in CI.

Two exclusions, both deliberate:

- `CHANGELOG.md` is the audit trail. Its historical entries record the counts
  in force at each release and must keep saying 165, 169 and so on.
- `examples/` holds dated validation reports from real publications. They are
  evidence of what the tool reported on the day, not claims about today.
"""

from __future__ import annotations

import re

import pytest

from conftest import REPO_ROOT, oasis_pub_check

INVENTORY = oasis_pub_check.conditions_inventory()
TOTAL = len(INVENTORY)
CLASSES = len({c["check"] for c in INVENTORY})

# Each pattern captures a number that is claimed to be either the condition
# total or the class total. Anchored on the noun so a count of packages,
# gates, pages or months cannot be swept in.
CONDITION_CLAIMS = [
    re.compile(r"(\d+) individual checks"),
    re.compile(r"(\d+) individual check conditions"),
    re.compile(r"(\d+) conditions"),
    re.compile(r"(\d+) checks"),
    re.compile(r"(\d+)-check "),
]
CLASS_CLAIMS = [
    re.compile(r"(\d+) check classes"),
    re.compile(r"(\d+) classes"),
]

DOCS = [
    "README.md",
    "PUBLICATION-QUALITY.md",
    "pub-check/README.md",
    "pub-check/CHECKS.md",
    "pub-check/AUTHORITIES.md",
]


def _svgs():
    return sorted(p for p in (REPO_ROOT / "assets").rglob("*.svg"))


def _claims(text, patterns):
    return [int(n) for pat in patterns for n in pat.findall(text)]


@pytest.mark.parametrize("rel", DOCS)
def test_documentation_advertises_the_current_condition_count(rel):
    text = (REPO_ROOT / rel).read_text(encoding="utf-8")
    wrong = [n for n in _claims(text, CONDITION_CLAIMS) if n != TOTAL]
    assert not wrong, (
        f"{rel} advertises {sorted(set(wrong))} conditions; the tool runs {TOTAL}. "
        f"Regenerate or correct it.")


@pytest.mark.parametrize("rel", DOCS)
def test_documentation_advertises_the_current_class_count(rel):
    text = (REPO_ROOT / rel).read_text(encoding="utf-8")
    wrong = [n for n in _claims(text, CLASS_CLAIMS) if n != CLASSES]
    assert not wrong, (
        f"{rel} advertises {sorted(set(wrong))} check classes; the tool has "
        f"{CLASSES}. Regenerate or correct it.")


def test_every_diagram_advertises_the_current_counts():
    """The SVG sources are what `assets/build.py` writes and what the PNGs are
    rendered from, so a stale count reaches the reader through both."""
    stale = {}
    for svg in _svgs():
        text = svg.read_text(encoding="utf-8")
        bad = ([n for n in _claims(text, CONDITION_CLAIMS) if n != TOTAL]
               + [n for n in _claims(text, CLASS_CLAIMS) if n != CLASSES])
        if bad:
            stale[svg.relative_to(REPO_ROOT).as_posix()] = sorted(set(bad))
    assert not stale, (
        f"diagrams carry stale counts {stale}; the tool runs {TOTAL} conditions "
        f"across {CLASSES} classes. Re-run assets/build.py --png.")


def test_the_readme_badge_advertises_the_current_counts():
    """The badge is a shields.io URL, so its numbers sit in query text the
    prose patterns above do not reach."""
    text = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    m = re.search(r"badge/checks-(\d+)_individual_%C2%B7_(\d+)_classes", text)
    assert m, "the checks badge is missing or its URL shape changed"
    assert (int(m.group(1)), int(m.group(2))) == (TOTAL, CLASSES)


def test_the_claim_patterns_actually_match_something():
    """A count check whose patterns match nothing would pass on any document.
    Prove the instrument reads the artifacts before trusting a green run."""
    catalog = (REPO_ROOT / "pub-check" / "CHECKS.md").read_text(encoding="utf-8")
    assert _claims(catalog, CONDITION_CLAIMS), "condition patterns matched nothing"
    assert _claims(catalog, CLASS_CLAIMS), "class patterns matched nothing"
    assert any(_claims(p.read_text(encoding="utf-8"),
                       CONDITION_CLAIMS + CLASS_CLAIMS) for p in _svgs()), \
        "no diagram matched any count pattern"
