# Copyright 2026 OASIS Open
# SPDX-License-Identifier: Apache-2.0
# Authored by Michael Coletta, Technical Advisor to OASIS Open.
"""fail-on-blockers: report-only runs.

DMLex (Sep 2026) kept a working draft whose only blockers were inherited from
the published standard and needed a TC decision; every run of its workflow
showed red. `continue-on-error` passed the job but left the step failed.
`fail-on-blockers: false` passes the step and says why in a warning. An
unreadable target must still fail. Runs the enforce step from action.yml as
the runner does.
"""
import subprocess

import pytest
import yaml

from conftest import REPO_ROOT


def _enforce():
    action = yaml.safe_load((REPO_ROOT / "action.yml").read_text())
    assert action["inputs"]["fail-on-blockers"]["default"] == "true"
    return next(s["run"] for s in action["runs"]["steps"] if s.get("name") == "Enforce gate result")


def _run(exit_code, fail_on_blockers, blockers="5"):
    env = {"PATH": "/usr/bin:/bin", "EXIT_CODE": exit_code, "BLOCKERS": blockers,
           "FAIL_ON_BLOCKERS": fail_on_blockers, "TARGET": "work/v1.1/wd01"}
    return subprocess.run(["bash", "-c", _enforce()], env=env, capture_output=True, text=True)


@pytest.mark.parametrize("code, fail_on, expected", [
    ("0", "true", 0), ("0", "false", 0),
    ("1", "true", 1),                       # default: a blocker fails
    ("1", "false", 0),                      # report-only: it passes
    ("2", "true", 2), ("2", "false", 2),    # unreadable target fails either way
    ("", "false", 2),                       # the gate never ran: fail
])
def test_the_step_exit_code(code, fail_on, expected):
    assert _run(code, fail_on).returncode == expected


def test_report_only_says_so_in_a_warning():
    out = _run("1", "false").stdout
    assert "::warning" in out and "5 blocker(s)" in out and "work/v1.1/wd01" in out


def test_a_failing_run_prints_no_report_only_warning():
    assert "::warning" not in _run("1", "true").stdout
