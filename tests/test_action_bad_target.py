# Copyright 2026 OASIS Open
# SPDX-License-Identifier: Apache-2.0
# Authored by Michael Coletta, Technical Advisor to OASIS Open.
"""A wrong `target:` path is the commonest first-run mistake a TC makes.

v1.5.0 answered it with three JSON tracebacks and an "exit code 1"
annotation from the summary step beside the gate's own exit code 2, so the
first thing a TC read was a crash and the code that means "blockers". Runs
the gate step and the summary step from action.yml as the runner does.
"""
import subprocess
import sys
from pathlib import Path

import yaml

from conftest import REPO_ROOT


def _steps():
    return yaml.safe_load((REPO_ROOT / "action.yml").read_text())["runs"]["steps"]


def test_a_missing_target_says_so_once_without_a_traceback(tmp_path):
    steps = _steps()
    gate = next(s["run"] for s in steps if s.get("id") == "pubcheck")
    summary = next(s["run"] for s in steps if s.get("name") == "Write step summary")
    work, temp = tmp_path / "work", tmp_path / "runner-temp"
    work.mkdir()
    temp.mkdir()
    # A report left by an earlier call in the same job must not survive.
    (work / "pubcheck-report").mkdir()
    (work / "pubcheck-report" / "pubcheck-report.json").write_text("{}")
    out, step_summary = tmp_path / "github-output", tmp_path / "summary.md"
    out.write_text("")
    env = {"PATH": f"{Path(sys.executable).parent}:/usr/bin:/bin",
           "ACTION_PATH": str(REPO_ROOT), "TARGET": "work/v2.1/CSD01", "EXTRA_ARGS": "",
           "REPORT_DIR": "pubcheck-report", "SUMMARY_TITLE": "",
           "RUNNER_TEMP": str(temp), "GITHUB_OUTPUT": str(out),
           "GITHUB_STEP_SUMMARY": str(step_summary), "PUB_CHECK_OFFLINE": "1"}

    ran = subprocess.run(["bash", "-c", gate], cwd=work, env=env,
                         capture_output=True, text=True)
    outputs = dict(line.split("=", 1) for line in out.read_text().splitlines())
    assert "Traceback" not in ran.stdout + ran.stderr, ran.stderr
    assert outputs["exit_code"] == "2"
    assert outputs["blockers"] == "" and outputs["report_json"] == ""
    assert "::error::oasis-pub-check could not read the target 'work/v2.1/CSD01'" in ran.stdout
    assert not (work / "pubcheck-report" / "pubcheck-report.json").exists()

    env["EXIT_CODE"] = outputs["exit_code"]
    result = subprocess.run(["bash", "--noprofile", "--norc", "-eo", "pipefail", "-c", summary],
                            cwd=work, env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert "Traceback" not in result.stderr
    text = step_summary.read_text()
    assert "The target could not be read (exit code 2)" in text
    assert "`work/v2.1/CSD01`" in text
