#!/usr/bin/env python3
# Copyright 2026 OASIS Open
# SPDX-License-Identifier: Apache-2.0
# Authored by Michael Coletta, Technical Advisor to OASIS Open.
"""Refuse a pull request that changes a check without an adversarial review.

A change to the checker must come with an independent attempt to break it,
recorded in the pull request body:

    ## Adversarial review

    Reviewer, mandate, the counterexamples tried, and for each one the test
    that pins it: tests/test_x.py::test_the_counterexample

The section passes when it names at least one test node id, every named node
id exists at the head, and the pull request added or modified each of those
tests. It also passes when it reads `not applicable: <reason>` (a pure
refactor or a message-text change), and then the reason is on the record.
A pull request that does not touch a gated path passes without a section.

    PR_BODY="..." check_gate_change_review.py --base <sha> --head <sha> [--repo DIR]

Exit 0 pass, 1 refused, 2 bad invocation. Standard library only. The body
arrives in an environment variable, never interpolated into a shell.
"""

from __future__ import annotations

import argparse
import ast
import os
import re
import subprocess
import sys

GATED = ("pub-check/oasis_pub_check.py",)
NODE = re.compile(r"(tests/[\w./-]+\.py)::(test_\w+)")


def git(repo: str, *args: str) -> str:
    return subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True,
                          check=True).stdout


def review_section(body: str) -> str | None:
    """The text under the '## Adversarial review' heading, up to the next
    heading of the same or higher level; None when there is no such heading."""
    m = re.search(r"(?im)^(#{1,3})\s*adversarial review\s*$", body or "")
    if not m:
        return None
    rest = body[m.end():]
    nxt = re.search(rf"(?m)^#{{1,{len(m.group(1))}}}\s+\S", rest)
    return (rest[:nxt.start()] if nxt else rest).strip()


def test_source(repo: str, rev: str, path: str, name: str) -> str | None:
    """Source text of test function `name` in `path` at `rev`, or None."""
    try:
        src = git(repo, "show", f"{rev}:{path}")
    except subprocess.CalledProcessError:
        return None
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return None
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return ast.get_source_segment(src, node)
    return None


def evaluate(body: str, base: str, head: str, repo: str = ".") -> tuple[bool, str]:
    changed = set(git(repo, "diff", "--name-only", f"{base}...{head}").split())
    gated = sorted(changed.intersection(GATED))
    if not gated:
        return True, "This pull request does not change a gated path; no review needed."
    section = review_section(body)
    if section is None:
        return False, (f"This pull request changes {', '.join(gated)} and its body has no "
                       f"'## Adversarial review' section. Record the independent review: "
                       f"the counterexamples tried and the tests/...py::test_... that pins each.")
    na = re.match(r"(?i)not applicable\s*:\s*(\S.*)", section)
    if na:
        return True, f"Adversarial review marked not applicable: {na.group(1).strip()}"
    nodes = NODE.findall(section)
    if not nodes:
        return False, ("The '## Adversarial review' section names no test node id "
                       "(tests/...py::test_...). Name the test that pins each counterexample, "
                       "or write 'not applicable: <reason>'.")
    problems = []
    for path, name in nodes:
        after = test_source(repo, head, path, name)
        if after is None:
            problems.append(f"{path}::{name} does not exist at the head of this pull request")
        elif test_source(repo, base, path, name) == after:
            problems.append(f"{path}::{name} was not added or modified by this pull request")
    if problems:
        return False, "; ".join(problems) + "."
    return True, f"Adversarial review pinned by {len(nodes)} test(s) this pull request adds or changes."


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--base", required=True)
    ap.add_argument("--head", required=True)
    ap.add_argument("--repo", default=".")
    a = ap.parse_args()
    try:
        ok, why = evaluate(os.environ.get("PR_BODY", ""), a.base, a.head, a.repo)
    except subprocess.CalledProcessError as e:
        print(f"git failed: {e.stderr or e}", file=sys.stderr)
        return 2
    print(("PASS: " if ok else "REFUSED: ") + why)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
