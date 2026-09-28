# Copyright 2026 OASIS Open
# SPDX-License-Identifier: Apache-2.0
# Authored by Michael Coletta, Technical Advisor to OASIS Open.
"""The copy-me converting workflow calls the reusable one correctly.

examples/converting-workflow.yml is what a TC copies; it must set only
inputs .github/workflows/convert-and-verify.yml defines, give every required
one, and call it at the release its own pa-ref default names. The reusable
workflow's steps must use only the tools the release ships. The run itself
is proven by MColetta-OASIS/lexidma, which calls it for DMLex.
"""

from __future__ import annotations

import re

import yaml

from conftest import REPO_ROOT

WORKFLOW = REPO_ROOT / ".github" / "workflows" / "convert-and-verify.yml"
EXAMPLE = REPO_ROOT / "examples" / "converting-workflow.yml"


def load(p):
    y = yaml.safe_load(p.read_text(encoding="utf-8"))
    y["on"] = y.get("on", y.get(True))  # YAML 1.1 reads the key `on` as True
    return y


def test_the_example_sets_only_inputs_the_workflow_defines_and_every_required_one():
    inputs = load(WORKFLOW)["on"]["workflow_call"]["inputs"]
    job = load(EXAMPLE)["jobs"]["convert-and-verify"]
    given = set(job["with"])
    assert given <= set(inputs), given - set(inputs)
    assert {k for k, v in inputs.items() if v.get("required")} <= given


def test_the_example_calls_the_release_the_workflow_runs():
    job = load(EXAMPLE)["jobs"]["convert-and-verify"]
    called = re.search(r"@(v\d+\.\d+\.\d+)$", job["uses"]).group(1)
    assert load(WORKFLOW)["on"]["workflow_call"]["inputs"]["pa-ref"]["default"] == called


def test_every_tool_the_workflow_runs_is_in_the_release():
    text = WORKFLOW.read_text(encoding="utf-8")
    for path in set(re.findall(r"_pa/([\w./-]+\.(?:py|sh))", text)):
        assert (REPO_ROOT / path).is_file(), path
    assert (REPO_ROOT / "action.yml").is_file(), "the gate step uses ./_pa, this repository's action"
