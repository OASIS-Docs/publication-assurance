# Copyright 2026 OASIS Open
# SPDX-License-Identifier: Apache-2.0
# Authored by Michael Coletta, Technical Advisor to OASIS Open.
"""The checks that need the This-stage base URL report NOT EVALUATED.

SARIF v2.2 csd01 (Oct 2026): the cover's autolinked This-stage URLs did not
parse, the base URL came back empty, and schema-id, revision-collision and
public-review-metadata returned without a word. One of them was hiding a real
$id BLOCKER. A check that could not run now says so, with the reason.
"""

from __future__ import annotations

import pytest

from conftest import CORPUS, oasis_pub_check, stage_from_corpus

THIS_BLOCKER = ("This-stage URL points at 'x.md' which is not a file in the "
                "package: https://docs.oasis-open.org/x/x.md")
ITEMS = {"md": "x.md", "pdf": "x.pdf"}


def not_evaluated(f):
    return sorted((x["severity"], x["check"]) for x in f.items
                  if x["message"].startswith("NOT EVALUATED"))


def schema_stage(tmp_path, stage="csd01"):
    d = tmp_path / "v1.0" / stage
    (d / "schema").mkdir(parents=True)
    (d / "schema" / "x.json").write_text('{"$id": "https://docs.oasis-open.org/x"}', encoding="utf-8")
    (d / "schema" / "x.xsd").write_text("<xs:schema/>", encoding="utf-8")
    return d


def run_check(base, stage_dir, stage, items, *prior):
    f = oasis_pub_check.Findings()
    for p in prior:
        f.add(oasis_pub_check.BLOCKER, "front-matter", p)
    oasis_pub_check.check_not_evaluated(base, str(stage_dir), "v1.0", stage, items, f)
    return f


def test_package_checks_block_and_network_checks_warn_under_a_this_stage_blocker(tmp_path):
    f = run_check("", schema_stage(tmp_path), "csd01", ITEMS, THIS_BLOCKER)
    assert not_evaluated(f) == [
        ("BLOCKER", "package-refs"), ("BLOCKER", "pdf-sync"), ("BLOCKER", "schema-id"),
        ("BLOCKER", "xml-namespace"),
        ("WARN", "public-review-metadata"), ("WARN", "revision-collision")]


def test_with_no_this_stage_blocker_every_not_evaluated_line_blocks(tmp_path):
    f = run_check("", schema_stage(tmp_path), "csd01", ITEMS,
                  "Latest-stage URL not under /v1.0/: https://x")
    assert {s for s, _ in not_evaluated(f)} == {"BLOCKER"}
    assert len(not_evaluated(f)) == 6


def test_only_the_checks_that_apply_are_reported(tmp_path):
    d = tmp_path / "v1.0" / "cs01"
    d.mkdir(parents=True)
    (d / "manifest.json").write_text("{}", encoding="utf-8")
    assert not_evaluated(run_check("", d, "cs01", {"html": "x.html"})) == [
        ("BLOCKER", "revision-collision")]


def test_offline_the_network_checks_are_not_reported(tmp_path, monkeypatch):
    monkeypatch.setenv("PUB_CHECK_OFFLINE", "1")
    f = run_check("", schema_stage(tmp_path), "csd01", {}, THIS_BLOCKER)
    assert not_evaluated(f) == [("BLOCKER", "schema-id"), ("BLOCKER", "xml-namespace")]


def test_a_parsed_base_reports_nothing(tmp_path):
    f = run_check("https://docs.oasis-open.org/x/v1.0/csd01/", schema_stage(tmp_path), "csd01", ITEMS)
    assert not_evaluated(f) == []


def _broken_cover(tmp_path, monkeypatch, old, new):
    monkeypatch.setenv("PUB_CHECK_OFFLINE", "1")
    stage = stage_from_corpus(tmp_path, CORPUS / "csaf" / "v2.1" / "csd01")
    md = stage / "csaf-v2.1-csd01.md"
    head, sep, tail = md.read_text(encoding="utf-8").partition("#### Previous stage")
    assert sep and head.count(old) == 3, "fixture cover changed shape"
    md.write_text(head.replace(old, new) + sep + tail, encoding="utf-8")
    f = oasis_pub_check.Findings()
    oasis_pub_check.run(str(stage), f)
    return f


@pytest.mark.parametrize("old,new", [
    ("/csaf-v2.1-csd01.", "/csaf-v2.1-csd01-renamed."),   # names no file in the package
    ("/csd01/csaf-v2.1-csd01.", "/csd02/csaf-v2.1-csd01."),  # a cover copied from another stage
], ids=["unparsed", "stale-stage"])
def test_a_cover_without_a_base_reports_the_skipped_checks(tmp_path, monkeypatch, old, new):
    """End to end on CSAF v2.1 csd01 (it ships JSON schemas): the schema-id,
    pdf-sync and package-refs checks that used to be skipped in silence now
    block, and a stale cover no longer compares the schemas with the wrong
    stage directory."""
    f = _broken_cover(tmp_path, monkeypatch, old, new)
    assert any(x["severity"] == "BLOCKER" and x["check"] == "front-matter" for x in f.items)
    assert not_evaluated(f) == [("BLOCKER", "package-refs"), ("BLOCKER", "pdf-sync"),
                                ("BLOCKER", "schema-id")]
    assert not [x for x in f.items if x["check"] == "schema-id"
                and not x["message"].startswith("NOT EVALUATED")]


def test_broken_json_is_still_reported_without_a_base(tmp_path):
    d = schema_stage(tmp_path)
    (d / "schema" / "broken.json").write_text("{", encoding="utf-8")
    f = oasis_pub_check.Findings()
    oasis_pub_check.check_schemas(str(d), "", "v1.0", "csd01", f)
    assert [x["message"] for x in f.items] == [
        "broken.json: not valid JSON (Expecting property name enclosed in double quotes: "
        "line 1 column 2 (char 1))"]
