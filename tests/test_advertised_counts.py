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

# A claim can be wrapped across a line break by the editor who wrote it, and
# "all 92\nconditions" then hides from a single-line pattern. It did: the
# worked-example paragraph in PUBLICATION-QUALITY.md carried a stale 92 for
# months while this file was green. Every document is matched with its
# whitespace collapsed.
WS = re.compile(r"\s+")

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


CORPUS_CLAIMS = [
    re.compile(r"corpus of (\d+) archived"),
    re.compile(r"regression_corpus-(\d+)_packages"),
    re.compile(r"Regression corpus: (\d+) packages"),
]

# A corpus package is a stage directory: the unit oasis_pub_check.py is
# pointed at. Version-root directories (the "latest version" copies) hold the
# same bytes again and are not separate submissions.
STAGE_DIR = re.compile(
    r"^(wd|csd|cs|cnd|cn|os|ps|psd|pn|pnd|errata|csprd|cnprd|cos)\d*$")
DELIVERY_SUFFIXES = {".html", ".pdf", ".docx", ".odt", ".md"}


def _corpus_packages():
    return sorted(
        d for d in (REPO_ROOT / "examples").rglob("*")
        if d.is_dir() and STAGE_DIR.match(d.name)
        and any(f.is_file() and f.suffix.lower() in DELIVERY_SUFFIXES
                for f in d.iterdir()))


def _claims(text, patterns):
    flat = WS.sub(" ", text)
    return [int(n) for pat in patterns for n in pat.findall(flat)]


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


@pytest.mark.parametrize("rel", ["README.md", "PUBLICATION-QUALITY.md",
                                 "pub-check/README.md"])
def test_documentation_advertises_the_corpus_that_is_here(rel):
    """The corpus size is advertised in three places and counted in none.
    It said 13 while the repository carried 12 stage packages."""
    here = len(_corpus_packages())
    text = (REPO_ROOT / rel).read_text(encoding="utf-8")
    wrong = [n for n in _claims(text, CORPUS_CLAIMS) if n != here]
    assert not wrong, (
        f"{rel} advertises a {sorted(set(wrong))}-package regression corpus; "
        f"examples/ holds {here} stage packages.")


def test_the_corpus_claim_patterns_actually_match_something():
    assert _claims((REPO_ROOT / "README.md").read_text(encoding="utf-8"),
                   CORPUS_CLAIMS), "corpus patterns matched nothing in README.md"
    assert len(_corpus_packages()) > 1, "the corpus walk found nothing"
