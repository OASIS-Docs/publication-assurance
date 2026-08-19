"""Smoke coverage over the checker's entry points.

These pin the CLI contract the runbook, the composite action and gate.py all
depend on: the exit-code semantics, the --json shape, the --list-checks
self-audit, and the fact that --emit-manifest writes both companion files.
They are deliberately shallow; the check semantics are not asserted here.
"""

from __future__ import annotations

import json

import pytest

from conftest import CORPUS, run_cli, stage_from_corpus

CSAF_CSD01 = CORPUS / "csaf" / "v2.1" / "csd01"


@pytest.fixture(scope="module")
def corpus_stage(tmp_path_factory):
    return stage_from_corpus(tmp_path_factory.mktemp("corpus"), CSAF_CSD01)


def test_list_checks_reports_a_registry_in_sync_with_the_ast():
    """--list-checks asserts the documented condition registry against an AST
    walk of the checker. A drifting registry must fail loudly, not print."""
    result = run_cli("--list-checks")

    assert result.returncode == 0, (
        f"--list-checks failed (exit {result.returncode}):\n{result.stderr}"
    )
    assert "individual checks across" in result.stdout, (
        f"--list-checks printed no check inventory:\n{result.stdout}"
    )
    assert "in sync with the AST" in result.stdout, (
        f"--list-checks did not confirm registry/AST parity:\n{result.stdout}"
    )


def test_a_directory_run_prints_findings_and_a_verdict(corpus_stage):
    result = run_cli(str(corpus_stage))

    assert result.returncode in (0, 1), (
        f"unexpected exit {result.returncode}:\n{result.stderr}"
    )
    assert "blocker(s)," in result.stdout, (
        f"no verdict line in the run summary:\n{result.stdout}"
    )
    expected = "NOT PUBLISHABLE" if result.returncode == 1 else "publishable"
    assert expected in result.stdout, (
        f"exit {result.returncode} contradicts the printed verdict:\n{result.stdout}"
    )


def test_json_output_carries_the_documented_keys(corpus_stage):
    result = run_cli("--json", str(corpus_stage))

    assert result.returncode in (0, 1), (
        f"unexpected exit {result.returncode}:\n{result.stderr}"
    )
    payload = json.loads(result.stdout)
    for key in ("target", "findings", "blockers", "conditions", "observed"):
        assert key in payload, (
            f"--json dropped the '{key}' key; consumers parse this shape. "
            f"got keys: {sorted(payload)}"
        )
    assert payload["blockers"] == sum(
        1 for item in payload["findings"] if item["severity"] == "BLOCKER"
    ), "the blocker count disagrees with the findings list"


def test_json_exit_code_tracks_the_blocker_count(corpus_stage):
    result = run_cli("--json", str(corpus_stage))
    payload = json.loads(result.stdout)

    assert result.returncode == (1 if payload["blockers"] else 0), (
        f"exit {result.returncode} with {payload['blockers']} blocker(s); "
        "gate.py and the composite action both branch on this"
    )


def test_emit_manifest_writes_both_companion_files(tmp_path):
    stage = stage_from_corpus(tmp_path, CSAF_CSD01)
    result = run_cli("--emit-manifest", str(stage))

    assert result.returncode in (0, 1), (
        f"--emit-manifest failed (exit {result.returncode}):\n{result.stderr}"
    )
    assert (stage / "manifest.json").exists(), (
        f"--emit-manifest wrote no manifest.json:\n{result.stdout}"
    )
    txt = list(stage.glob("*-manifest.txt"))
    assert len(txt) == 1, (
        f"expected exactly one Work Product Manifest File, found: {txt}"
    )
    assert "manifest.json in this directory" in \
        txt[0].read_text(encoding="utf-8"), (
            "--emit-manifest shipped both files but the manifest does not "
            "name its JSON companion"
        )


def test_a_missing_target_exits_two_without_a_traceback(tmp_path):
    result = run_cli(str(tmp_path / "no-such-dir"))

    assert result.returncode == 2, (
        f"expected exit 2 for a bad target, got {result.returncode}"
    )
    assert "Traceback" not in result.stderr, (
        f"a bad target raised instead of reporting:\n{result.stderr}"
    )


def test_no_target_and_no_list_checks_is_a_usage_error():
    result = run_cli()

    assert result.returncode != 0, "an empty invocation must not succeed"
    assert "target is required" in result.stderr, (
        f"unexpected usage error:\n{result.stderr}"
    )
