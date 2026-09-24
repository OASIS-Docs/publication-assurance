"""A pull request that changes a check must record an adversarial review.

PR #9 (Sep 2026) exempted stage-uri-live Latest URIs. Its first draft passed
its own tests and CI, and an independent agent then built an input on which
the exemption hid a broken Latest URI. That review happened only because the
author chose to ask for one. `.github/scripts/check_gate_change_review.py`
makes it a condition of merge. Any PR that touches the checker must carry an
`## Adversarial review` section in its body, naming at least one test node id
that the PR adds or modifies, or saying `not applicable: <reason>`.

The fixtures are this repository's own history. e1196cf..2dc6783 is PR #9's
range: it changed the checker and added
tests/test_stage_uri_live_first_stage.py, whose
test_a_mis_cited_previous_stage_does_not_hide_a_broken_latest pins the
reviewer's counterexample. 204a4a1 changed a test and no checker code.
"""

from __future__ import annotations

import importlib.util
import subprocess

import pytest

from conftest import REPO_ROOT

SCRIPT = REPO_ROOT / ".github/scripts/check_gate_change_review.py"


def load():
    spec = importlib.util.spec_from_file_location("gate_review", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def have(rev):
    return subprocess.run(["git", "-C", str(REPO_ROOT), "cat-file", "-e", f"{rev}^{{commit}}"],
                          capture_output=True).returncode == 0


pytestmark = pytest.mark.skipif(
    not all(have(r) for r in ("e1196cf", "2dc6783", "204a4a1")),
    reason="needs full history: CI checks out with fetch-depth 0")

PR9 = ("e1196cf", "2dc6783")
PINNED = ("tests/test_stage_uri_live_first_stage.py::"
          "test_a_mis_cited_previous_stage_does_not_hide_a_broken_latest")


def verdict(body, rng=PR9):
    return load().evaluate(body, *rng, repo=str(REPO_ROOT))


def test_the_script_exists_and_is_stdlib_only():
    src = SCRIPT.read_text()
    imports = {line.split()[1].split(".")[0] for line in src.splitlines()
               if line.startswith(("import ", "from ")) and "__future__" not in line}
    assert imports <= {"argparse", "ast", "os", "re", "subprocess", "sys"}, imports


def test_pr9_with_its_pinned_counterexample_passes():
    ok, why = verdict(f"Fix.\n\n## Adversarial review\n\nrev agent. Pinned by {PINNED}.\n")
    assert ok, why


def test_pr9_without_a_review_section_fails():
    ok, why = verdict("Fix the first stage.\n\nTests pass.\n")
    assert not ok and "Adversarial review" in why


def test_an_empty_or_na_section_fails():
    for text in ("", "n/a", "none", "Reviewed, looks fine."):
        ok, why = verdict(f"## Adversarial review\n\n{text}\n\n## Other\n")
        assert not ok, text


def test_not_applicable_with_a_reason_passes_and_is_on_the_record():
    ok, why = verdict("## Adversarial review\n\nnot applicable: message text only\n")
    assert ok and "message text only" in why


def test_not_applicable_without_a_reason_fails():
    ok, _ = verdict("## Adversarial review\n\nnot applicable:\n")
    assert not ok


def test_a_node_id_the_pr_did_not_touch_fails():
    ok, why = verdict("## Adversarial review\n\n"
                      "tests/test_cli_smoke.py::test_list_checks_reports_a_registry_in_sync_with_the_ast\n")
    assert not ok and "not added or modified" in why


def test_a_node_id_that_does_not_exist_fails():
    ok, why = verdict("## Adversarial review\n\n"
                      "tests/test_stage_uri_live_first_stage.py::test_no_such_thing\n")
    assert not ok and "does not exist" in why


def test_one_bad_node_id_among_good_ones_fails():
    body = (f"## Adversarial review\n\n{PINNED}\n"
            "tests/test_stage_uri_live_first_stage.py::test_no_such_thing\n")
    assert not verdict(body)[0]


def test_a_pr_that_does_not_touch_the_checker_needs_nothing():
    ok, why = verdict("Docs only.", ("204a4a1^", "204a4a1"))
    assert ok and "does not change" in why


def test_the_cli_exit_code_follows_the_verdict(tmp_path):
    body = tmp_path / "body.md"
    body.write_text("no review here")
    r = subprocess.run(["python3", str(SCRIPT), "--base", PR9[0], "--head", PR9[1],
                        "--repo", str(REPO_ROOT)], env={"PR_BODY": body.read_text(), "PATH": "/usr/bin:/bin"},
                       capture_output=True, text=True)
    assert r.returncode == 1, r.stdout + r.stderr
    r = subprocess.run(["python3", str(SCRIPT), "--base", PR9[0], "--head", PR9[1],
                        "--repo", str(REPO_ROOT)],
                       env={"PR_BODY": f"## Adversarial review\n{PINNED}", "PATH": "/usr/bin:/bin"},
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
