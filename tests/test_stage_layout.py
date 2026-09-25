"""Regression fixtures for how the checker reads a package's place in the
docs.oasis-open.org layout, and for two title defects found beside it.

Every stage, version and errata determination reads path segments. Three
targets gave it the wrong segments:

- a version root (csaf/v2.0, which holds the Latest-stage copies) read its
  TC directory 'csaf' as the version, so version-naming, title-version and
  front-matter all reported "package is 'csaf'";
- a package zip was checked from a temporary directory, so the stage read
  as 'pub_check_xxxx' and the version as the temp parent ('T' on macOS);
- an errata1 or errata001 directory had no check of its own, and the
  title citing it took the blame instead.

title-oasis-prefix also tag-stripped the entity-decoded <title>, deleting
text such as '<Bar>' and losing its match.
"""

from __future__ import annotations

import json
import os
import shutil
import zipfile

from conftest import CORPUS, oasis_pub_check, run_cli, stage_from_corpus

Findings = oasis_pub_check.Findings
BLOCKER = oasis_pub_check.BLOCKER

CSAF_V20 = CORPUS / "csaf" / "v2.0"
CSAF_ERRATA_OS = CSAF_V20 / "errata01" / "os"
ERRATA_OS_ZIP = CSAF_ERRATA_OS / "csaf-v2.0-errata01-os.zip"


def _of(f, check: str) -> list[dict]:
    return [x for x in f.items if x["check"] == check]


def _run(stage, monkeypatch) -> Findings:
    monkeypatch.setenv("PUB_CHECK_OFFLINE", "1")
    f = Findings()
    oasis_pub_check.run(str(stage), f)
    return f


def test_version_root_reads_its_own_version(tmp_path, monkeypatch):
    """csaf/v2.0 is its own version directory. It is still not a stage
    package, and stage-name still says so."""
    root = tmp_path / "csaf" / "v2.0"
    shutil.copytree(CSAF_V20, root)
    assert oasis_pub_check.parse_stage(str(root)) == ("v2.0", "v2.0")

    f = _run(root, monkeypatch)

    assert _of(f, "version-naming") == [], _of(f, "version-naming")
    assert not [x for x in f.items if "package is 'csaf'" in x["message"]], f.items
    assert [x["message"] for x in _of(f, "stage-name")] == [
        "Stage 'v2.0' is not a recognized stage token."]


def test_title_oasis_prefix_keeps_decoded_angle_brackets():
    """Red-team counterexample: 'OASIS Foo &lt;Bar&gt; Version 2.0' decodes to
    'OASIS Foo <Bar> Version 2.0'; tag-stripping that deleted '<Bar>', no
    heading matched, and the OASIS prefix went unreported."""
    title = "OASIS Foo &lt;Bar&gt; Version 2.0"
    html = (f"<html><head><title>{title}</title></head><body>"
            f"<h1>{title}</h1><h1>1. Introduction</h1></body></html>")

    f = Findings()
    oasis_pub_check.check_frontmatter_title_oasis_prefix(html, "csd01", f)

    assert f.observed["title-oasis-prefix"].get("title_match") == "exact", f.observed
    tp = _of(f, "title-oasis-prefix")
    assert [x["severity"] for x in tp] == [BLOCKER], tp


def _errata_package(tmp_path, folder: str):
    stage = tmp_path / "csaf" / "v2.0" / folder / "os"
    shutil.copytree(CSAF_ERRATA_OS, stage)
    return stage


def test_malformed_errata_folder_is_refused_by_name(tmp_path, monkeypatch):
    """errata1 and errata001 break the two-digit /errata01/ rule. The folder
    is refused by name, and the title 'Version 2.0 Errata 01', which cites
    the same Errata, is not blamed for it."""
    for folder in ("errata1", "errata001"):
        f = _run(_errata_package(tmp_path / folder, folder), monkeypatch)
        msgs = [x["message"] for x in _of(f, "stage-name")]
        assert msgs == [f"Errata directory '{folder}' is missing its two-digit number (e.g. errata01)."], msgs
        assert _of(f, "title-version") == [], _of(f, "title-version")


def test_malformed_errata_folder_still_checks_the_errata_number(tmp_path, monkeypatch):
    """The folder finding does not excuse a title citing another Errata."""
    stage = _errata_package(tmp_path, "errata1")
    page = stage / "csaf-v2.0-errata01-os.html"
    html = page.read_text(encoding="utf-8")
    assert html.count("Errata 01</title>") == 1, "fixture precondition"
    html = html.replace("Errata 01</title>", "Errata 02</title>").replace(
        "Errata 01</h1big>", "Errata 02</h1big>")
    page.write_text(html, encoding="utf-8")

    f = _run(stage, monkeypatch)

    tv = [x for x in _of(f, "title-version") if "composition" in x["message"]]
    assert [x["severity"] for x in tv] == [BLOCKER], _of(f, "title-version")


def test_stage_with_one_digit_names_the_two_digit_rule():
    f = Findings()
    oasis_pub_check.check_stage_name("csd1", f)
    assert [x["message"] for x in f.items] == ["Stage 'csd1' is missing its two-digit number (e.g. csd01)."]


def test_zip_stage_layout_from_the_package_stem():
    """zip_stage_layout now returns the parsed (abbrev, ver, errata, stage)
    parts, or None, so main() can decide where to place the package instead
    of trusting a joined path string."""
    layout = oasis_pub_check.zip_stage_layout
    assert layout("/x/csaf-v2.0-errata01-os.zip", []) == ("csaf", "v2.0", "errata01", "os")
    assert layout("/x/odata-v4.01-os-part1-protocol.zip", []) == ("odata", "v4.01", "", "os")
    assert layout("/x/renamed.zip", ["kmip-spec-v3.0-csd02.html", "kmip-spec-v3.0-csd02.md"]) \
        == ("kmip-spec", "v3.0", "", "csd02")
    assert layout("/x/renamed.zip", ["notes.html"]) is None


def test_zip_stage_layout_refuses_a_traversal_segment():
    """Red-team counterexample: '..-v2.0-os.zip' parses to abbrev '..', which
    would compose a path outside tmp/pkg. Refused at parse time, not caught
    later by a rename that already escaped."""
    assert oasis_pub_check.zip_stage_layout("/x/..-v2.0-os.zip", []) is None


def _zip_from_dir(zip_path, src_dir, arc_prefix=""):
    with zipfile.ZipFile(zip_path, "w") as z:
        for r, _dirs, files in os.walk(src_dir):
            for n in files:
                p = os.path.join(r, n)
                arc = arc_prefix + os.path.relpath(p, src_dir)
                z.write(p, arc)
    return zip_path


def test_zip_name_does_not_override_a_contradicting_inner_path(tmp_path):
    """Red-team counterexample: a zip holding csaf/v2.0/cs03/csaf-v2.0-os.*
    (the os corpus files, at their own path under a cs03 stage folder),
    named csaf-v2.0-os.zip. The rename used to discard that inner path and
    let the zip's own filename overrule it, so the '-cs03' mismatch and the
    This-stage URL blockers vanished. The stage directory's own path carries
    a vN.N segment, so it is left in place and the mismatch still fires."""
    zpath = _zip_from_dir(tmp_path / "csaf-v2.0-os.zip", CSAF_V20 / "os",
                          arc_prefix="csaf/v2.0/cs03/")
    r = run_cli(str(zpath), "--json")
    d = json.loads(r.stdout)

    assert d["observed"]["stage-name"]["stage_directory"] == "cs03"
    assert d["observed"]["version-naming"]["version_directory"] == "v2.0"
    fn = [x["message"] for x in _checks(d, "filenames") if x["severity"] == BLOCKER]
    assert any("does not end in '-cs03'" in m for m in fn), d["findings"]
    assert r.returncode == 1


def test_zip_subfolder_keeps_its_own_directory_name(tmp_path):
    """Red-team counterexample: a zip named csaf-v2.0-os.zip holding a single
    'csd01/' folder of delivery items. The folder's own name is the real
    stage; overriding it with the zip's 'os' would hide a mismatch just like
    the cs03 case above, so the package is placed at abbrev/ver/<subfolder>,
    not abbrev/ver/<stage from the zip name>."""
    zpath = _zip_from_dir(tmp_path / "csaf-v2.0-os.zip", CSAF_V20 / "os",
                          arc_prefix="csd01/")
    r = run_cli(str(zpath), "--json")
    d = json.loads(r.stdout)

    assert d["observed"]["stage-name"]["stage_directory"] == "csd01"
    assert d["observed"]["version-naming"]["version_directory"] == "v2.0"


def test_zip_errata_stem_beats_a_zip_filename_missing_it(tmp_path):
    """Red-team counterexample: csaf-v2.0-os-x.zip holding the errata01/os
    corpus at the zip root. The zip's own stem parses as stage 'os' with a
    stray '-x' tail and loses the errata segment; the root-level delivery
    item csaf-v2.0-errata01-os.md still carries it, and a root-level stem is
    now preferred over the zip filename stem, so the package checks under
    errata01 with no title-version composition finding."""
    zpath = _zip_from_dir(tmp_path / "csaf-v2.0-os-x.zip", CSAF_ERRATA_OS)
    r = run_cli(str(zpath), "--json")
    d = json.loads(r.stdout)

    assert d["observed"]["stage-name"]["stage_directory"] == "os"
    tv = [x for x in d["findings"] if x["check"] == "title-version" and "composition" in x["message"]]
    assert tv == [], tv
    assert r.returncode == 0, d["findings"]


def test_zip_is_checked_under_its_publication_path(tmp_path):
    """Checked from the temp directory, the errata01/os zip reported 31
    findings built on a stage 'pub_check_xxxx' and a version 'T'. Under its
    publication path it must report what the stage directory reports."""
    env_off = {"PUB_CHECK_OFFLINE": "1"}
    import os
    import subprocess
    import sys
    from conftest import PUB_CHECK
    def check(target):
        r = subprocess.run([sys.executable, str(PUB_CHECK), str(target), "--json"],
                           capture_output=True, text=True, env={**os.environ, **env_off})
        return r.returncode, json.loads(r.stdout)

    rc_zip, zj = check(ERRATA_OS_ZIP)
    stage = stage_from_corpus(tmp_path / "v2.0", CSAF_ERRATA_OS)
    (stage / ERRATA_OS_ZIP.name).unlink()
    rc_dir, dj = check(stage)

    assert not [x for x in zj["findings"] if "pub_check_" in x["message"]], zj["findings"]
    assert zj["observed"]["stage-name"]["stage_directory"] == "os"
    assert zj["observed"]["version-naming"]["version_directory"] == "v2.0"
    assert _checks(zj, "stage-name", "version-naming", "title-version", "filenames") == \
        _checks(dj, "stage-name", "version-naming", "title-version", "filenames") == []
    assert rc_zip == 0, zj["findings"]


def _checks(j, *names):
    return [x for x in j["findings"] if x["check"] in names]


def test_zip_entry_escaping_the_extraction_dir_is_refused(tmp_path):
    bad = tmp_path / "evil-v1.0-csd01.zip"
    with zipfile.ZipFile(bad, "w") as z:
        z.writestr("../escaped.html", "<html></html>")
    r = run_cli(str(bad))
    assert r.returncode == 2, (r.stdout, r.stderr)
    assert "escapes extraction dir" in r.stderr


def _cli_json(target):
    import os
    import subprocess
    import sys
    from conftest import PUB_CHECK
    r = subprocess.run([sys.executable, str(PUB_CHECK), str(target), "--json"],
                       capture_output=True, text=True,
                       env={**os.environ, "PUB_CHECK_OFFLINE": "1"})
    return r.returncode, json.loads(r.stdout)


def test_zip_layout_skips_auxiliary_stems_beside_the_delivery(tmp_path):
    """Red team round 2 (P6): a redline and a comments file sort before
    csaf-v2.0-os at the zip root, and the first root stem set the layout, so
    the package checked as stage cs02 and failed filenames."""
    src = tmp_path / "src"
    shutil.copytree(CSAF_V20 / "os", src)
    for z in src.glob("*.zip"):
        z.unlink()
    (src / "csaf-v2.0-cs02-to-os-redline.html").write_text("<html></html>")
    (src / "csaf-v2.0-csd01-comments.md").write_text("# comments\n")
    zpath = _zip_from_dir(tmp_path / "csaf-v2.0-os.zip", src)
    _, j = _cli_json(zpath)
    assert j["observed"]["stage-name"]["stage_directory"] == "os", j["observed"]["stage-name"]
    assert _checks(j, "stage-name", "filenames") == [], _checks(j, "stage-name", "filenames")


def test_zip_subfolder_repeating_the_wp_abbrev_keeps_its_errata(tmp_path):
    """Red team round 2 (P3b): csaf-v2.0-errata01-os.zip holding csaf/os/...
    was placed at csaf/v2.0/csaf/os, dropping errata01, and title-version
    blamed the correct 'Errata 01' title."""
    zpath = _zip_from_dir(tmp_path / "csaf-v2.0-errata01-os.zip", CSAF_ERRATA_OS, "csaf/os/")
    _, j = _cli_json(zpath)
    assert j["observed"]["stage-name"]["stage_directory"] == "os"
    assert j["observed"]["version-naming"]["version_directory"] == "v2.0"
    assert _checks(j, "title-version", "stage-name", "filenames") == [], j["findings"]


def test_unparseable_zip_is_named_by_the_zip_not_the_temp_dir(tmp_path):
    """Red team round 2 (P8): a zip whose name and contents give no layout
    was checked from tmp/raw, so messages named 'raw' and 'pub_check_xxxx'."""
    src = tmp_path / "src"
    src.mkdir()
    for ext in ("md", "html"):
        shutil.copy(CSAF_V20 / "os" / f"csaf-v2.0-os.{ext}", src / f"spec.{ext}")
    zpath = _zip_from_dir(tmp_path / "delivery.zip", src)
    _, j = _cli_json(zpath)
    msgs = [x["message"] for x in j["findings"]]
    assert not [m for m in msgs if "pub_check_" in m or "'raw'" in m], msgs
    assert "Stage 'delivery.zip' is not a recognized stage token." in msgs, msgs
