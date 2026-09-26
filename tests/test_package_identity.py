"""Regression fixtures for five naming gaps a red-team review found in the
package-identity checks. Before this change each case below passed with no
finding:

1. a plain OS package (csaf-v2.0-os.*) filed under errata01/os;
2. two packages' document identifiers in one stage directory, of which only
   one was graded;
3. a package zip named as a different document identifier than the one it
   holds (the cover URL's WP-abbrev directory is NOT compared: on the real
   site KMIP files kmip-spec-v1.4-os.* under .../kmip/spec/v1.4/os/);
4. a numbered OS stage directory (os01), although naming-directives.txt 5.2
   says 'The os stage abbreviation is never used with a revision number';
5. an upper-case Errata01 parent directory, although stage abbreviations
   are lower case, and the title citing it was blamed instead.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import zipfile

from conftest import CORPUS, PUB_CHECK, oasis_pub_check

Findings = oasis_pub_check.Findings
BLOCKER = oasis_pub_check.BLOCKER

CSAF_V20 = CORPUS / "csaf" / "v2.0"
CSAF_V21_CSD01 = CORPUS / "csaf" / "v2.1" / "csd01"


def _run(stage, monkeypatch, **kw) -> Findings:
    monkeypatch.setenv("PUB_CHECK_OFFLINE", "1")
    f = Findings()
    oasis_pub_check.run(str(stage), f, **kw)
    return f


def _msgs(f, check: str) -> list[str]:
    return [x["message"] for x in f.items if x["check"] == check]


def _copy(src, dest):
    shutil.copytree(src, dest)
    return dest


def test_plain_os_package_under_an_errata_directory_is_flagged(tmp_path, monkeypatch):
    stage = _copy(CSAF_V20 / "os", tmp_path / "csaf" / "v2.0" / "errata01" / "os")
    f = _run(stage, monkeypatch)
    assert ("Delivery filename 'csaf-v2.0-os' does not end in '-errata01-os' (the stage "
            "directory name, under its Errata directory).") in _msgs(f, "filenames"), f.items


def test_errata_package_under_its_errata_directory_passes(tmp_path, monkeypatch):
    stage = _copy(CSAF_V20 / "errata01" / "os", tmp_path / "csaf" / "v2.0" / "errata01" / "os")
    f = _run(stage, monkeypatch)
    assert _msgs(f, "filenames") == [], f.items


def test_second_package_in_one_stage_directory_is_flagged(tmp_path, monkeypatch):
    stage = _copy(CSAF_V20 / "cs03", tmp_path / "csaf" / "v2.0" / "cs03")
    for ext in ("md", "html"):
        shutil.copy(CSAF_V20 / "os" / f"csaf-v2.0-os.{ext}", stage)
    f = _run(stage, monkeypatch)
    assert ("Delivery items do not share one basename: ['csaf-v2.0-cs03', 'csaf-v2.0-os']"
            in _msgs(f, "filenames")), f.items


def test_a_different_document_with_a_tail_is_still_a_second_package(tmp_path, monkeypatch):
    """Red team, PR 31: exempting every tailed stem let a genuinely different
    document (other-doc-v1.0-os-part1-core) through. Only an auxiliary file of
    the package's own document is exempt."""
    stage = _copy(CSAF_V20 / "os", tmp_path / "csaf" / "v2.0" / "os")
    (stage / "other-doc-v1.0-os-part1-core.md").write_text("# other\n")
    f = _run(stage, monkeypatch)
    assert [m for m in _msgs(f, "filenames")
            if "share one basename" in m and "other-doc-v1.0-os-part1-core" in m], f.items


def test_the_packages_own_redline_and_comments_are_not_a_second_package(tmp_path, monkeypatch):
    stage = _copy(CSAF_V20 / "os", tmp_path / "csaf" / "v2.0" / "os")
    (stage / "csaf-v2.0-cs02-to-os-redline.html").write_text("<html></html>")
    (stage / "csaf-v2.0-csd01-comments.md").write_text("# comments\n")
    f = _run(stage, monkeypatch)
    assert not [m for m in _msgs(f, "filenames") if "share one basename" in m], f.items


def test_an_earlier_reviews_side_file_is_not_a_second_package(tmp_path, monkeypatch):
    """A comment-resolution log for an earlier review names another stage
    and is not a second package."""
    stage = _copy(CSAF_V20 / "cs03", tmp_path / "csaf" / "v2.0" / "cs03")
    (stage / "csaf-v2.0-csd02-comment-resolution-log.html").write_text("<html></html>")
    f = _run(stage, monkeypatch)
    assert not [m for m in _msgs(f, "filenames") if "share one basename" in m], f.items


def test_url_directory_may_differ_from_the_filename_abbrev(tmp_path, monkeypatch):
    """Red-team counterexample: KMIP v1.x files are kmip-spec-v1.4-os.* and
    the published cover URL is .../kmip/spec/v1.4/os/..., so the directory
    above the version is not the filename's WP-abbrev on the real site. A
    rule requiring /kmip-spec/v1.4/ put 381 false BLOCKERs on published
    KMIP packages; the URL is held only to its version and stage."""
    stage = _copy(CSAF_V21_CSD01, tmp_path / "csaf" / "v2.1" / "csd01")
    md = stage / "csaf-v2.1-csd01.md"
    text = md.read_text(encoding="utf-8")
    assert "/csaf/csaf/v2.1/csd01/" in text, "fixture precondition"
    md.write_text(text.replace("/csaf/csaf/v2.1/csd01/", "/csaf/spec/v2.1/csd01/"),
                  encoding="utf-8")
    f = _run(stage, monkeypatch)
    assert not [m for m in _msgs(f, "front-matter") if "URL does not contain" in m], f.items


def _cli(target):
    r = subprocess.run([sys.executable, str(PUB_CHECK), str(target), "--json"],
                       capture_output=True, text=True,
                       env={**os.environ, "PUB_CHECK_OFFLINE": "1"})
    return r.returncode, json.loads(r.stdout)


def test_zip_named_for_another_document_is_flagged(tmp_path):
    src = CSAF_V20 / "errata01" / "os"
    bad = tmp_path / "wrongtc-v2.0-errata01-os.zip"
    good = tmp_path / "csaf-v2.0-errata01-os.zip"
    for z in (bad, good):
        with zipfile.ZipFile(z, "w") as zf:
            for p in sorted(src.rglob("*")):
                if p.is_file() and p.suffix != ".zip":
                    zf.write(p, p.relative_to(src).as_posix())
    _, bj = _cli(bad)
    rc, gj = _cli(good)
    share = lambda j: [x["message"] for x in j["findings"] if "share one basename" in x["message"]]
    assert share(bj) == ["Delivery items do not share one basename: "
                         "['csaf-v2.0-errata01-os', 'wrongtc-v2.0-errata01-os.zip']"], bj["findings"]
    assert share(gj) == [] and rc == 0, gj["findings"]


def test_zip_name_that_is_no_document_identifier_is_not_compared(tmp_path):
    """Red-team counterexample: a browser download renamed the zip
    ('... (1).zip', 'package.zip'), and a version root's Latest zip
    (kmip-spec-v3.0.zip) carries no stage. Neither names another document,
    so neither is a second package."""
    src = CSAF_V20 / "errata01" / "os"
    for name in ("package.zip", "csaf-v2.0-errata01-os (1).zip", "csaf-v2.0.zip"):
        z = tmp_path / name
        with zipfile.ZipFile(z, "w") as zf:
            for p in sorted(src.rglob("*")):
                if p.is_file() and p.suffix != ".zip":
                    zf.write(p, p.relative_to(src).as_posix())
        rc, j = _cli(z)
        assert not [x for x in j["findings"] if "share one basename" in x["message"]], (name, j["findings"])


def test_numbered_os_stage_is_refused():
    f = Findings()
    oasis_pub_check.check_stage_name("os01", f)
    assert _msgs(f, "stage-name") == [
        "Stage 'os01' is not a recognized stage token. The os stage abbreviation is "
        "never used with a revision number."]
    ok = Findings()
    oasis_pub_check.check_stage_name("os", ok)
    assert ok.items == []


def test_upper_case_errata_directory_is_refused_by_name(tmp_path, monkeypatch):
    stage = _copy(CSAF_V20 / "errata01" / "os", tmp_path / "csaf" / "v2.0" / "Errata01" / "os")
    f = _run(stage, monkeypatch)
    assert _msgs(f, "stage-name") == [
        "Errata directory 'Errata01' is not a recognized stage token. Stage "
        "abbreviations are lower case (errata01)."], f.items
    assert _msgs(f, "title-version") == [], f.items
    assert _msgs(f, "filenames") == [], f.items


def test_upper_case_stage_directory_names_the_lower_case_form():
    f = Findings()
    oasis_pub_check.check_stage_name("CSD01", f)
    assert _msgs(f, "stage-name") == [
        "Stage 'CSD01' is not a recognized stage token. Stage abbreviations are lower case (csd01)."]


def test_an_errata_token_is_not_reread_as_the_stage():
    """Red team round 2: 'x-v1.0-errata01-csd01_fixed' failed the errata
    reading on its '_fixed' tail and was re-read with errata01 as the stage,
    so a stray copy blocked an errata package while the same stray beside a
    plain csd01 package ('x-v1.0-csd01_fixed') was ignored."""
    parse = oasis_pub_check.parse_package_stem
    assert parse("x-v1.0-errata01-csd01_fixed") is None
    assert parse("x-v1.0-csd01_fixed") is None
    assert parse("x-v1.0-errata01-csd01") == ("x", "v1.0", "errata01", "csd01")
    assert parse("x-v1.0-errata01-os-complete") == ("x", "v1.0", "errata01", "os")
    assert parse("csaf-v2.0-errata01") == ("csaf", "v2.0", "", "errata01")


def test_upper_case_numbered_os_names_a_valid_form():
    f = Findings()
    oasis_pub_check.check_stage_name("OS01", f)
    assert _msgs(f, "stage-name") == [
        "Stage 'OS01' is not a recognized stage token. Stage abbreviations are lower case (os)."]
