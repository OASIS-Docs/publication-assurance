# Copyright 2026 OASIS Open
# SPDX-License-Identifier: Apache-2.0
# Authored by Michael Coletta, Technical Advisor to OASIS Open.
"""Regression fixtures for the Work Product Manifest File emitter.

Two defects, both found staging UBL v2.5 as an OASIS Standard:

- 5c3dd27: the document title was copied out of the rendered HTML <title>
  without unescaping, so an entity reached the published manifest verbatim.
- 7cbe512: the preamble promised a manifest.json companion whether or not one
  was emitted, so a text-manifest-only publication shipped a dangling
  reference at a citable URL.
"""

from __future__ import annotations

import json
import shutil
import subprocess

import pytest

from conftest import FIXTURES, oasis_pub_check

emit_manifest_txt = oasis_pub_check.emit_manifest_txt

# Matched on the invariant clause, not the whole sentence: the pre-7cbe512
# preamble wrapped the same claim across two lines, and the no-change
# guard below must hold against that phrasing too.
JSON_CLAIM = "manifest.json in this directory"


@pytest.fixture()
def manifest_stage(tmp_path):
    """A writable copy of the entity-title fixture; the emitter writes into the
    directory it reads."""
    stage = tmp_path / "v2.5" / "os"
    shutil.copytree(FIXTURES / "manifest_title" / "v2.5" / "os", stage)
    return stage


def test_manifest_title_unescapes_html_entities(manifest_stage):
    """UBL renders its title as 'Universal Business Language Version&nbsp;2.5',
    which published as that literal string in the manifest."""
    out = emit_manifest_txt(str(manifest_stage), "v2.5", "os")
    title = next(line for line in open(out, encoding="utf-8")
                 if line.startswith("Title:"))

    assert "&nbsp;" not in title and "&amp;" not in title, (
        f"an HTML entity reached the published manifest title: {title!r}"
    )
    assert title.split(":", 1)[1].strip() == (
        "Universal Business Language Version 2.5 & Errata"
    ), f"unexpected manifest title: {title!r}"


def test_manifest_preamble_omits_the_json_claim_when_no_json_ships(manifest_stage):
    """A publication shipping the text manifest alone must not point readers at
    a manifest.json that is not there."""
    out = emit_manifest_txt(str(manifest_stage), "v2.5", "os", with_json=False)
    text = open(out, encoding="utf-8").read()

    assert not (manifest_stage / "manifest.json").exists(), (
        "fixture invalid: this test must run with no JSON companion present"
    )
    assert JSON_CLAIM not in text, (
        "the manifest promises a manifest.json companion that was never "
        f"emitted:\n{text.split('=====')[0]}"
    )


def test_manifest_preamble_keeps_the_json_claim_when_json_ships(manifest_stage):
    """--emit-manifest writes both files, so the default must be unchanged."""
    out = emit_manifest_txt(str(manifest_stage), "v2.5", "os")
    text = open(out, encoding="utf-8").read()

    assert JSON_CLAIM in text, (
        "the manifest no longer names its machine-readable companion:\n"
        f"{text.split('=====')[0]}"
    )


def test_manifest_records_the_stage_and_version_it_was_given(manifest_stage):
    out = emit_manifest_txt(str(manifest_stage), "v2.5", "os")
    text = open(out, encoding="utf-8").read()

    assert "Version:        v2.5" in text, f"version not recorded:\n{text}"
    assert "Approval stage: os" in text, f"approval stage not recorded:\n{text}"


# source.commit (SARIF v2.2 csd01, Oct 2026): the stage was assembled inside
# the ops workspace, a different git repository, and manifest.json recorded
# that repository's HEAD as the package's source commit.
emit_manifest = oasis_pub_check.emit_manifest


def _git(cwd, *args):
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.org",
                           *args], cwd=cwd, capture_output=True, text=True,
                          check=True).stdout.strip()


def _commit_of(stage):
    out = emit_manifest(str(stage), "v2.5", "os")
    return json.load(open(out, encoding="utf-8"))["source"]["commit"]


@pytest.fixture()
def repo(tmp_path, monkeypatch):
    monkeypatch.delenv("GITHUB_SHA", raising=False)
    _git(tmp_path, "init", "-q")
    (tmp_path / "README.md").write_text("ops workspace\n", encoding="utf-8")
    _git(tmp_path, "add", "README.md")
    _git(tmp_path, "commit", "-q", "-m", "unrelated")
    return tmp_path


def test_a_stage_the_enclosing_repo_does_not_hold_records_no_commit(repo, manifest_stage):
    stage = repo / "work" / "v2.5" / "os"
    shutil.copytree(manifest_stage, stage)
    assert _commit_of(stage) == ""


def test_a_stage_committed_as_is_records_head(repo, manifest_stage):
    stage = repo / "tc" / "v2.5" / "os"
    shutil.copytree(manifest_stage, stage)
    _git(repo, "add", "tc")
    _git(repo, "commit", "-q", "-m", "stage")
    assert _commit_of(stage) == _git(repo, "rev-parse", "HEAD")
    # Emitting again must not count its own manifest.json as a local change.
    _git(repo, "add", "tc")
    _git(repo, "commit", "-q", "-m", "manifest")
    assert _commit_of(stage) == _git(repo, "rev-parse", "HEAD")


def test_a_stage_with_uncommitted_changes_records_no_commit(repo, manifest_stage):
    stage = repo / "tc" / "v2.5" / "os"
    shutil.copytree(manifest_stage, stage)
    _git(repo, "add", "tc")
    _git(repo, "commit", "-q", "-m", "stage")
    (stage / "extra.html").write_text("<p>not committed</p>\n", encoding="utf-8")
    assert _commit_of(stage) == ""


def test_github_sha_still_wins(repo, manifest_stage, monkeypatch):
    monkeypatch.setenv("GITHUB_SHA", "0123456789abcdef0123456789abcdef01234567")
    assert _commit_of(manifest_stage) == "0123456789abcdef0123456789abcdef01234567"


def test_a_stage_whose_renders_the_repo_ignores_records_no_commit(repo, manifest_stage):
    """The ops workspace tracks a batch's text files and ignores its renders:
    the stage looked committed and clean, but HEAD does not hold the HTML."""
    (repo / ".gitignore").write_text("*.html\n", encoding="utf-8")
    stage = repo / "tc" / "v2.5" / "os"
    shutil.copytree(manifest_stage, stage)
    (stage / "UBL-2.5-os.md").write_text("# Universal Business Language\n", encoding="utf-8")
    _git(repo, "add", ".gitignore", "tc")
    _git(repo, "commit", "-q", "-m", "text files only")
    assert any(p.suffix == ".html" for p in stage.rglob("*")), "fixture must carry an HTML render"
    assert _git(stage, "ls-files"), "fixture must track some of the stage"
    assert _commit_of(stage) == ""
