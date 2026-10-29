# Copyright 2026 OASIS Open
# SPDX-License-Identifier: Apache-2.0
# Authored by Michael Coletta, Technical Advisor to OASIS Open.
"""Multi-Part Work Products, Naming Directives v1.7 s6.1 Option 1: each part
sits in its own [partNumber]-[partName]/ folder under the stage directory,
https://docs.oasis-open.org/[tc]/[wp]/[version]/[stage]/[partN-name]/[doc-id].[ext],
and the stage directory itself holds no document.

OData Version 4.02 CS01 (Oct 2026) is such a package. Checked at its stage
directory, the checker found no delivery items and checked nothing. Checked
as a zip whose members start with the part folders, it read the first part
folder as the stage. Both must check every part as a document of the stage.
"""

from __future__ import annotations

import json
import zipfile

from conftest import run_cli

SITE = "https://docs.oasis-open.org/tc/wp/v1.0"
PARTS = ("part1-intro", "part2-core")


def _md(part: str, todo: bool) -> str:
    stem = f"wp-v1.0-cs01-{part}"
    return (
        f"# Widget Protocol Version 1.0. {part}\n\n"
        "## Committee Specification 01\n\n## 29 October 2026\n\n"
        "#### This stage:\n"
        + "".join(f"{SITE}/cs01/{part}/{stem}.{e}\\\n" for e in ("md", "html", "pdf"))
        + "\n#### Latest stage:\n"
        f"{SITE}/wp-v1.0-{part}.html\n\n"
        "#### Technical Committee:\n[Widget TC](https://www.oasis-open.org/)\n\n"
        "# 1 Introduction\n\nText.\n"
        + ("\nTODO: finish this section.\n" if todo else "")
    )


def _html(part: str) -> str:
    return (f"<!DOCTYPE html><html><head><title>Widget Protocol Version 1.0. {part}"
            "</title></head><body><h1>Widget Protocol Version 1.0</h1></body></html>")


def _stage(tmp_path):
    stage = tmp_path / "tc" / "wp" / "v1.0" / "cs01"
    for part in PARTS:
        d = stage / part
        d.mkdir(parents=True)
        stem = f"wp-v1.0-cs01-{part}"
        (d / f"{stem}.md").write_text(_md(part, todo=part == "part2-core"), encoding="utf-8")
        (d / f"{stem}.html").write_text(_html(part), encoding="utf-8")
        (d / f"{stem}.pdf").write_bytes(b"%PDF-1.4\n%%EOF\n")
    return stage


def _findings(target):
    p = run_cli(str(target), "--json")
    assert p.stdout, p.stderr
    d = json.loads(p.stdout)
    return [(x["severity"], x["check"], x["message"]) for x in d["findings"]], d["observed"]


def _assert_checked_as_parts_of_the_stage(findings, observed):
    msgs = [m for _s, _c, m in findings]
    assert not any("No delivery items found" in m for m in msgs), msgs
    # stage and version come from cs01 and v1.0, never from a part folder
    assert not [x for x in findings if x[1] in ("stage-name", "version-naming")], findings
    assert not [x for x in findings if x[1] == "front-matter" and x[0] == "BLOCKER"], findings
    assert observed["stage-name"]["stage_directory"] == "cs01"
    assert observed["filenames"]["multi_part_option_1_parts"] == "part1-intro, part2-core"
    # every part is checked: the planted TODO in part 2 is reported, named for its part
    todo = [x for x in findings if x[1] == "residue" and "Editor TODO" in x[2]]
    assert len(todo) == 1 and todo[0][0] == "BLOCKER", todo
    assert todo[0][2].startswith("part2-core: Editor TODO left in markdown line "), todo


def test_a_multi_part_option_1_stage_directory_checks_every_part(tmp_path):
    findings, observed = _findings(_stage(tmp_path))
    _assert_checked_as_parts_of_the_stage(findings, observed)
    # the part 1 documents are checked too, under their own part name
    assert any(m.startswith("part1-intro: ") for _s, _c, m in findings), findings


def test_a_multi_part_option_1_zip_reads_its_stage_from_the_zip_name(tmp_path):
    stage = _stage(tmp_path)
    zpath = tmp_path / "wp-v1.0-cs01.zip"
    with zipfile.ZipFile(zpath, "w") as z:
        for p in sorted(stage.rglob("*")):
            if p.is_file():
                z.write(p, p.relative_to(stage).as_posix())
    assert sorted(zipfile.ZipFile(zpath).namelist())[0].startswith("part1-intro/")
    findings, observed = _findings(zpath)
    assert not any("part1-intro' is not a recognized stage" in m for _s, _c, m in findings)
    _assert_checked_as_parts_of_the_stage(findings, observed)


def test_a_part_named_for_another_stage_is_reported_not_skipped(tmp_path):
    """pr81-reviewer counterexample b2: part 1 named for cs01, part 2 for
    csd01. Part 2 must be checked and its filenames reported, not dropped."""
    stage = _stage(tmp_path)
    part2 = stage / "part2-core"
    for p in list(part2.iterdir()):
        p.rename(part2 / p.name.replace("-cs01-", "-csd01-"))
    findings, observed = _findings(stage)
    assert observed["filenames"]["multi_part_option_1_parts"] == "part1-intro, part2-core"
    assert ("BLOCKER", "filenames",
            "part2-core: Delivery filename 'wp-v1.0-csd01-part2-core' does not end in "
            "'-cs01' (the stage directory name).") in findings, findings
    # part 2 is still checked: its planted TODO is reported
    assert any(m.startswith("part2-core: Editor TODO") for _s, _c, m in findings), findings


def test_parts_are_checked_in_part_number_order(tmp_path):
    """pr81-reviewer counterexample d: part10 comes after part2."""
    stage = _stage(tmp_path)
    d = stage / "part10-extra"
    d.mkdir()
    for ext in ("md", "html", "pdf"):
        src = stage / "part1-intro" / f"wp-v1.0-cs01-part1-intro.{ext}"
        (d / f"wp-v1.0-cs01-part10-extra.{ext}").write_bytes(src.read_bytes())
    _findings_list, observed = _findings(stage)
    assert (observed["filenames"]["multi_part_option_1_parts"]
            == "part1-intro, part2-core, part10-extra")
