# Copyright 2026 OASIS Open
# SPDX-License-Identifier: Apache-2.0
# Authored by Michael Coletta, Technical Advisor to OASIS Open.
"""A Word package with a stray .md in its stage root is still a Word package.

find_delivery_items falls back to the shortest stem per format, so a stage
root holding kmip-ug-v3.0-cnd02.docx and a README.md (or a
comment-resolution-log.md) was read as a Markdown package with that file as
its source: every front-matter check ran on the README and blocked. A source
named for the stage now wins over one that is not; a stage-named .md still
makes the package a Markdown package.
"""

from __future__ import annotations

import pytest

from conftest import oasis_pub_check

WORD_TRACK = "Word-authored package"


def run(tmp_path, names, monkeypatch):
    monkeypatch.setenv("PUB_CHECK_OFFLINE", "1")
    stage = tmp_path / "v3.0" / "cnd02"
    stage.mkdir(parents=True)
    for n in names:
        (stage / n).write_text("# Readme\n\nNotes.\n" if n.endswith(".md") else "x",
                               encoding="utf-8")
    f = oasis_pub_check.Findings()
    oasis_pub_check.run(str(stage), f)
    return f


def word_track(f):
    return any(x["check"] == "track" and WORD_TRACK in x["message"] for x in f.items)


def md_cover_read(f):
    return any("found in the markdown" in x["message"] for x in f.items)


@pytest.mark.parametrize("stray", ["README.md", "kmip-ug-v3.0-cnd02-comment-resolution-log.md"])
def test_a_stray_md_beside_a_stage_named_docx_is_a_word_package(tmp_path, monkeypatch, stray):
    f = run(tmp_path, ["kmip-ug-v3.0-cnd02.docx", "kmip-ug-v3.0-cnd02.html",
                       "kmip-ug-v3.0-cnd02.pdf", stray], monkeypatch)
    assert word_track(f)
    assert not md_cover_read(f)


def test_a_stage_named_md_still_makes_a_markdown_package(tmp_path, monkeypatch):
    f = run(tmp_path, ["x-v3.0-cnd02.md", "x-v3.0-cnd02.docx", "x-v3.0-cnd02.html",
                       "x-v3.0-cnd02.pdf"], monkeypatch)
    assert not word_track(f)
    assert md_cover_read(f)


def test_authoritative_source_prefers_the_file_named_for_the_stage(tmp_path):
    stage = tmp_path / "v3.0" / "cnd02"
    items = {"md": str(stage / "README.md"), "docx": str(stage / "kmip-ug-v3.0-cnd02.docx")}
    assert oasis_pub_check.authoritative_source(items, str(stage)) == "docx"
    items["md"] = str(stage / "kmip-ug-v3.0-cnd02.md")
    assert oasis_pub_check.authoritative_source(items, str(stage)) == "md"
    assert oasis_pub_check.authoritative_source({"md": str(stage / "README.md")}, str(stage)) == "md"


def test_with_nothing_named_for_the_stage_every_file_stays_checked(tmp_path, monkeypatch):
    """Nothing named for the stage (here only by case): the README must not
    cost the .docx its own filename BLOCKERs (adversarial review, 14 Oct 2026)."""
    f = run(tmp_path, ["KMIP-UG-v3.0-CND02.docx", "kmip-ug-v3.0-cnd02x.html",
                       "kmip-ug-v3.0-cnd02x.pdf", "README.md"], monkeypatch)
    docx_blockers = [x["message"] for x in f.items
                     if x["severity"] == "BLOCKER" and "KMIP-UG-v3.0-CND02" in x["message"]]
    assert any("ixed-case" in m or "case" in m.lower() for m in docx_blockers), docx_blockers


def test_a_multipart_stage_named_docx_beside_a_readme_is_a_word_package(tmp_path, monkeypatch):
    f = run(tmp_path, ["odf-v3.0-cnd02-part1-introduction.docx", "odf-v3.0-cnd02-part1-introduction.html",
                       "odf-v3.0-cnd02-part1-introduction.pdf", "README.md"], monkeypatch)
    assert word_track(f)
    assert not md_cover_read(f)
