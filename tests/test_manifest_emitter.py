"""Regression fixtures for the Work Product Manifest File emitter.

Two defects, both found staging UBL v2.5 as an OASIS Standard:

- 5c3dd27: the document title was copied out of the rendered HTML <title>
  without unescaping, so an entity reached the published manifest verbatim.
- 7cbe512: the preamble promised a manifest.json companion whether or not one
  was emitted, so a text-manifest-only publication shipped a dangling
  reference at a citable URL.
"""

from __future__ import annotations

import shutil

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
