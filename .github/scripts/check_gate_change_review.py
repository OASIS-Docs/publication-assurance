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

GATED = re.compile(r"^pub-check/[^/]+\.py$")   # the checker and any module beside it
NODE = re.compile(r"(tests/[\w./-]+\.py)::((?:[A-Z]\w*::)?test_\w+)")


def git(repo: str, *args: str) -> str:
    return subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True,
                          check=True).stdout


def review_section(body: str) -> str | None:
    """The text under the 'Adversarial review' heading (any level from # to
    ####, or a bold line), up to the next heading of the same or a higher
    level. HTML comments and fenced code are removed first, so nothing in
    them counts. None when there is no such heading."""
    body = re.sub(r"<!--.*?-->", "", (body or "").replace("\r\n", "\n"), flags=re.S)
    body = re.sub(r"(?ms)^(```|~~~).*?^\1[^\n]*$", "", body)
    m = re.search(r"(?im)^(#{1,4}|\*\*)\s*adversarial review\b[^\n]*$", body)
    if not m:
        return None
    rest = body[m.end():]
    level = len(m.group(1)) if m.group(1).startswith("#") else 4
    nxt = re.search(rf"(?m)^#{{1,{level}}}\s+\S", rest)
    return (rest[:nxt.start()] if nxt else rest).strip()


def test_source(repo: str, rev: str, path: str, name: str) -> str | None:
    """The AST of test `name` (a function, or Class::method) in `path` at
    `rev`, dumped without positions, so a comment or whitespace edit is not a
    change. None when the file or the test is absent, or when the test is not
    one pytest collects: a test_*.py file and a test_* function that asserts
    something (an assert, or a call such as pytest.raises)."""
    try:
        src = git(repo, "show", f"{rev}:{path}")
    except subprocess.CalledProcessError:
        return None
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return None
    if not re.fullmatch(r"test_\w+\.py", path.rsplit("/", 1)[-1]):
        return None
    scope, _, func = name.rpartition("::")
    nodes = tree.body
    if scope:
        cls = next((n for n in nodes if isinstance(n, ast.ClassDef) and n.name == scope), None)
        nodes = cls.body if cls else []
    for node in nodes:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == func:
            checks = any(isinstance(n, (ast.Assert, ast.Raise, ast.With)) or
                         (isinstance(n, ast.Call) and "raises" in ast.dump(n.func))
                         for n in ast.walk(node))
            return ast.dump(node, include_attributes=False) if checks else None
    return None


def evaluate(body: str, base: str, head: str, repo: str = ".") -> tuple[bool, str]:
    changed = set()
    for line in git(repo, "diff", "--name-status", "-M", f"{base}...{head}").splitlines():
        changed.update(line.split("\t")[1:])      # both sides of a rename
    gated = sorted(p for p in changed if GATED.match(p))
    if not gated:
        return True, "This pull request does not change a gated path; no review needed."
    section = review_section(body)
    if section is None:
        return False, (f"This pull request changes {', '.join(gated)} and its body has no "
                       f"'## Adversarial review' section. Record the independent review: "
                       f"the counterexamples tried and the tests/...py::test_... that pins each.")
    na = re.search(r"(?im)^\s*not applicable\s*:[ \t]*(\S.*)$", section)
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
            problems.append(f"{path}::{name} does not exist at the head of this pull request, "
                            f"or is not a collected test that asserts something")
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
