# Copyright 2026 OASIS Open
# SPDX-License-Identifier: Apache-2.0
# Authored by Michael Coletta, Technical Advisor to OASIS Open.
"""harvest/harvest.py: every gate run's records become candidates for the
gate (proposal 013). Run on the TC Administration records of Aug-Sep 2026
it found the OData template and filenames false positives still raised,
and the package-refs directory false positive gone."""

from __future__ import annotations

import json
import subprocess
import sys

from conftest import CORPUS, REPO_ROOT

HARVEST = REPO_ROOT / "harvest" / "harvest.py"


def records(tmp_path):
    d = tmp_path / "records"
    d.mkdir()
    stage = str(CORPUS / "csaf" / "v2.1" / "csd01")
    (d / "v.json").write_text(json.dumps({
        "slug": "csaf-v2.1-csd01", "total_checks": 170, "target_local_path": stage,
        "condition_detail": [
            {"check": "package-refs", "result": "BLOCKER"},
            {"check": "template", "result": "PASS"}]}))
    (d / "a.json").write_text(json.dumps({"slug": "csaf-v2.1-csd01", "findings": [
        {"id": "F1", "classification": "external", "severity": "minor",
         "title": "One cross-reference uses a tab: URL scheme", "body": "..."},
        {"id": "F2", "classification": "process", "severity": "major", "title": "Ballot", "body": "..."},
        {"id": "F3", "classification": "external", "severity": "minor",
         "title": "A link-mismatch the gate already reports", "body": "..."}]}))
    adj = tmp_path / "adj.json"
    adj.write_text(json.dumps([{"slug": "csaf-v2.1-csd01", "check": "package-refs",
                                "verdict": "false-positive", "source": "a ticket"}]))
    return d, adj


def run(*args):
    return subprocess.run([sys.executable, str(HARVEST), *map(str, args)], capture_output=True, text=True)


def test_the_records_become_candidates(tmp_path):
    d, adj = records(tmp_path)
    r = run(d, "--adjudications", adj, "--json", tmp_path / "h.json")
    assert r.returncode == 0, r.stderr
    h = json.loads((tmp_path / "h.json").read_text())
    assert list(h["adjudicated_false_positives"]) == ["package-refs"]
    assert [m["id"] for m in h["found_by_hand"]] == ["F1"], "process findings and ones a check names are not candidates"
    assert "template" in h["never_fires"] and "package-refs" not in h["never_fires"]


def test_rerun_reports_what_the_current_gate_no_longer_raises(tmp_path):
    d, adj = records(tmp_path)
    r = run(d, "--rerun", "--json", tmp_path / "h.json")
    assert r.returncode == 0, r.stderr
    changed = json.loads((tmp_path / "h.json").read_text())["verdicts_changed"]
    assert changed and ["package-refs", "BLOCKER"] in changed[0]["no_longer_raised"]


def test_candidates_are_written_as_speculative_proposals(tmp_path):
    d, adj = records(tmp_path)
    props = tmp_path / "proposals"
    props.mkdir()
    (props / "013-learn.md").write_text("x")
    r = run(d, "--adjudications", adj, "--proposals", props)
    assert r.returncode == 0, r.stderr
    written = sorted(p.name for p in props.glob("0*.md"))
    assert written[0] == "013-learn.md" and written[1].startswith("014-narrow-package-refs")
    assert "Status: speculative" in (props / written[1]).read_text()
