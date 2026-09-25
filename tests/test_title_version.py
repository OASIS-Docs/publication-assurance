"""Regression fixtures for title-version's title resolution.

title-version checks the Version token in the rendered cover-page title. It
reads the <title> text and first confirms that exactly one title heading
carries it. It looked only at <h1>, but the CSAF markdown template renders its
cover title in <h1big>, the cover-title element the OASIS markdown stylesheet
defines. On every CSAF package the count was zero, and title-version reported
'Not evaluated: blocked by an upstream html-residue defect' while html-residue
had raised nothing: its D1 duplicate-title finding fires only above one.

Both now count the same elements through one helper, so title-version blames
html-residue only in the state where html-residue has raised its D1 BLOCKER.
"""

from __future__ import annotations

import pytest

from conftest import CORPUS, oasis_pub_check, stage_from_corpus

Findings = oasis_pub_check.Findings
BLOCKER, INFO = oasis_pub_check.BLOCKER, oasis_pub_check.INFO

CSAF_CSD01 = CORPUS / "csaf" / "v2.1" / "csd01"
CSAF_ERRATA_OS = CORPUS / "csaf" / "v2.0" / "errata01" / "os"


def _html(title: str, body: str) -> str:
    return (f"<html><head><title>{title}</title></head><body>"
            f'<p><img alt="OASIS Logo" src="logo.png"/></p>{body}'
            f'<h1 id="introduction">1. Introduction</h1>'
            f'<p><a href="#introduction">Introduction</a></p></body></html>')


def _of(f, check: str) -> list[dict]:
    return [x for x in f.items if x["check"] == check]


def _run_corpus(tmp_path, monkeypatch, corpus_stage):
    monkeypatch.setenv("PUB_CHECK_OFFLINE", "1")
    stage = stage_from_corpus(tmp_path, corpus_stage)
    f = Findings()
    oasis_pub_check.run(str(stage), f)
    return f


def test_csaf_h1big_cover_title_is_evaluated(tmp_path, monkeypatch):
    """The lead's reproduction: CSAF v2.1 csd01, whose cover title is
    <h1big>Common Security Advisory Framework Version 2.1</h1big>. html-residue
    passes, so title-version must evaluate the title, not blame it."""
    html = (CSAF_CSD01 / "csaf-v2.1-csd01.html").read_text(encoding="utf-8")
    assert "<h1big" in html and "<h1 id=\"common-security" not in html, (
        "fixture precondition: the cover title is in <h1big> and in no <h1>")

    f = _run_corpus(tmp_path, monkeypatch, CSAF_CSD01)

    assert _of(f, "html-residue") == [], _of(f, "html-residue")
    assert _of(f, "title-version") == [], _of(f, "title-version")
    obs = f.observed["title-version"]
    assert obs.get("version_tokens_found") == "1", obs
    assert obs.get("pkg_version") == "2.1", obs
    assert "evaluated" not in obs, obs


def test_csaf_h1big_cover_title_resolves_for_title_oasis_prefix(tmp_path, monkeypatch):
    """title-oasis-prefix shares the heading classification and was blind to
    <h1big> the same way: it skipped every CSAF package as 'ambiguous'."""
    f = _run_corpus(tmp_path, monkeypatch, CSAF_CSD01)
    obs = f.observed["title-oasis-prefix"]
    assert obs.get("title_match") == "exact", obs
    assert obs.get("title_source") == "Common Security Advisory Framework Version 2.1", obs


def test_duplicate_title_defers_to_the_html_residue_finding():
    """The title in <h1big> and again in an <h1>: the PDF cover renders it
    twice. html-residue raises D1, and title-version defers to that finding
    and says so."""
    title = "Widget Exchange Format Version 1.0"
    html = _html(title, f"<h1big>{title}</h1big><h1>{title}</h1>")

    f = Findings()
    oasis_pub_check.check_html(html, "wef-v1.0-csd01", f)
    oasis_pub_check.check_title_version(html, "v1.0", "csd01", False, f)

    d1 = [x for x in _of(f, "html-residue") if "lint D1" in x["message"]]
    assert [x["severity"] for x in d1] == [BLOCKER], _of(f, "html-residue")
    assert "appears in 2 <h1> elements" in d1[0]["message"]
    tv = _of(f, "title-version")
    assert [x["severity"] for x in tv] == [INFO], tv
    assert "html-residue D1 finding" in tv[0]["message"], tv
    assert f.observed["title-version"]["title_headings"] == "2"


def test_title_in_no_heading_does_not_blame_html_residue():
    """No heading carries the <title> text. html-residue has nothing to
    report, so title-version must name the real reason."""
    html = _html("Widget Exchange Format Version 1.0",
                 "<h1big>Something Else Entirely</h1big>")

    f = Findings()
    oasis_pub_check.check_html(html, "wef-v1.0-csd01", f)
    oasis_pub_check.check_title_version(html, "v1.0", "csd01", False, f)

    assert _of(f, "html-residue") == [], _of(f, "html-residue")
    tv = _of(f, "title-version")
    assert [x["severity"] for x in tv] == [INFO], tv
    assert "html-residue" not in tv[0]["message"], tv
    assert "matches no <h1> or <h1big> heading" in tv[0]["message"], tv


def test_h1big_title_with_a_wrong_version_is_now_caught():
    """The blind spot hid real defects: an <h1big> cover title citing another
    Version was never graded."""
    title = "Widget Exchange Format Version 1.1"
    html = _html(title, f"<h1big>{title}</h1big>")

    f = Findings()
    oasis_pub_check.check_title_version(html, "v1.0", "csd01", False, f)

    tv = _of(f, "title-version")
    assert [x["severity"] for x in tv] == [BLOCKER], tv
    assert "title has '1.1', package is '1.0'" in tv[0]["message"], tv


@pytest.mark.parametrize("suffix", [" Errata 01", " Plus Errata 03"])
def test_errata_suffix_is_accepted_on_an_errata_package_only(suffix):
    """Evaluating CSAF's <h1big> titles exposed the published OS Errata title
    'Common Security Advisory Framework Version 2.0 Errata 01'. naming-
    directives.txt Section 4 gives Errata their own construction, so the
    suffix passes on an Errata package and stays a defect anywhere else."""
    title = "Widget Exchange Format Version 1.0" + suffix
    html = _html(title, f"<h1big>{title}</h1big>")

    on_errata = Findings()
    oasis_pub_check.check_title_version(html, "v1.0", "os", False, on_errata, errata=True)
    assert _of(on_errata, "title-version") == [], _of(on_errata, "title-version")

    elsewhere = Findings()
    oasis_pub_check.check_title_version(html, "v1.0", "os", False, elsewhere)
    tv = _of(elsewhere, "title-version")
    assert [x["severity"] for x in tv] == [BLOCKER], tv
    assert "Version composition does not follow" in tv[0]["message"], tv


def test_published_csaf_errata_os_title_passes(tmp_path, monkeypatch):
    """End to end: run() must detect the errata01 directory and pass it on."""
    f = _run_corpus(tmp_path / "v2.0", monkeypatch, CSAF_ERRATA_OS)
    assert f.observed["title-version"].get("version_tokens_found") == "1", f.observed
    assert _of(f, "title-version") == [], _of(f, "title-version")
