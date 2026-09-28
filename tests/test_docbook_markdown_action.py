# Copyright 2026 OASIS Open
# SPDX-License-Identifier: Apache-2.0
# Authored by Michael Coletta, Technical Advisor to OASIS Open.
"""The docbook-markdown action: a TC's one step to a Markdown edition.

Runs the action's convert step as the runner does, against a stand-in
converter, so the contract holds without the tools installed: the outputs are
written whether the check passes or fails, a failed check fails the step, and
an empty published-html means no check at all.
"""
import subprocess
from pathlib import Path

import pytest
import yaml

from conftest import REPO_ROOT

ACTION = REPO_ROOT / "docbook-markdown" / "action.yml"


def _action():
    return yaml.safe_load(ACTION.read_text())


def _convert_step():
    return next(s for s in _action()["runs"]["steps"] if s.get("id") == "convert")["run"]


def test_the_inputs_a_tc_sets():
    inputs = _action()["inputs"]
    assert inputs["source"]["required"] and inputs["profile"]["required"]
    assert inputs["published-html"]["default"] == ""
    assert set(_action()["outputs"]) == {"markdown", "verification", "package"}


def _run(tmp_path, result_line, status, published="https://example.org/spec.html"):
    root = tmp_path / "pa"
    (root / "docbook-markdown").mkdir(parents=True)
    conv = root / "converters" / "docbook-to-markdown"
    conv.mkdir(parents=True)
    seen = tmp_path / "args.txt"
    (conv / "build.sh").write_text(
        "#!/usr/bin/env bash\n"
        f"printf '%s\\n' \"$@\" > {seen}\n"
        'echo "# spec" > "$4/spec-v1.0-os.md"\n'
        f"echo '{result_line}'\nexit {status}\n")
    (conv / "build.sh").chmod(0o755)
    out, summary = tmp_path / "github-output", tmp_path / "summary.md"
    out.write_text("")
    env = {"PATH": "/usr/bin:/bin", "ACTION_PATH": str(root / "docbook-markdown"),
           "SOURCE": "spec/src", "PROFILE": "dmlex", "PUBLISHED": published,
           "OUTPUT": str(tmp_path / "edition"), "RUNNER_TEMP": str(tmp_path),
           "GITHUB_OUTPUT": str(out), "GITHUB_STEP_SUMMARY": str(summary)}
    # The runner's own invocation for a composite step.
    r = subprocess.run(["bash", "--noprofile", "--norc", "-e", "-o", "pipefail", "-c", _convert_step()], env=env, capture_output=True, text=True, cwd=tmp_path)
    outputs = dict(l.split("=", 1) for l in out.read_text().splitlines() if "=" in l)
    return r, outputs, seen.read_text().splitlines(), summary.read_text()


def test_a_passing_check_passes_and_says_so(tmp_path):
    r, outputs, args, summary = _run(tmp_path, "RESULT: PASS", 0)
    assert r.returncode == 0, r.stderr
    assert outputs["verification"] == "PASS"
    assert outputs["markdown"].endswith("spec-v1.0-os.md")
    assert args[:2] == ["--profile", "dmlex"] and args[-1] == "https://example.org/spec.html"
    assert "**PASS**" in summary
    assert "::notice title=Markdown edition::spec-v1.0-os.md matches the published HTML" in r.stdout


def test_a_failed_check_records_fail_before_failing_the_step(tmp_path):
    r, outputs, _, summary = _run(tmp_path, "RESULT: FAIL", 1)
    assert r.returncode == 1
    assert outputs["verification"] == "FAIL" and "**FAIL**" in summary
    assert "::error title=Markdown edition::" in r.stdout


def test_no_published_html_means_no_check(tmp_path):
    r, outputs, args, _ = _run(tmp_path, "done", 0, published="")
    assert r.returncode == 0
    assert outputs["verification"] == "skipped"
    assert outputs["markdown"].endswith("spec-v1.0-os.md")
    assert len(args) == 4, args          # --profile NAME SOURCE OUT, nothing after


def test_the_shipped_example_uses_this_action():
    wf = yaml.safe_load((REPO_ROOT / "examples" / "docbook-markdown-workflow.yml").read_text())
    steps = wf["jobs"]["markdown-edition"]["steps"]
    assert any(s.get("uses", "").startswith("OASIS-Docs/publication-assurance/docbook-markdown@") for s in steps)


def test_the_upload_runs_on_a_current_node():
    """upload-artifact@v4 targets Node.js 20, which GitHub deprecated; every
    run of v1.11.0 carried that warning."""
    uses = [s.get("uses", "") for s in _action()["runs"]["steps"]]
    upload = next(u for u in uses if u.startswith("actions/upload-artifact@"))
    assert int(upload.split("@v")[1].split(".")[0]) >= 7, upload
