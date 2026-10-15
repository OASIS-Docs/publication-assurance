# Copyright 2026 OASIS Open
# SPDX-License-Identifier: Apache-2.0
# Authored by Michael Coletta, Technical Advisor to OASIS Open.
"""No text pub-check prints may use the word gate, gated, gates or gating.

Validation reports are read by TC editors. "Gate" is internal jargon for them:
the v2.2 CSD01 report carried "gated on the anchor text" four times. The plain
words are "checked against", "checks" or "check result".

What this scans, and why it is wide:

- every string a check can print comes from a string literal in
  oasis_pub_check.py (finding messages, f-string pieces, the values and the
  KEY NAMES passed to `observe`, which a report prints as "key: value", and
  the condition registry behind `--list-checks`). Scanning every non-docstring
  string literal and every keyword name in the module therefore covers all of
  them, including text built in a variable and passed to `f.add` later, which
  a scan limited to the arguments of the `f.add(...)` call would miss;
- the registry is also scanned through `conditions_inventory()`, the exact
  structure `--list-checks`, CHECKS.md and the validation report read.

What it deliberately does not scan: comments, docstrings and identifiers.
Those never reach a report. Code may say "gate" internally.
"""

from __future__ import annotations

import ast
import re

from conftest import PUB_CHECK, oasis_pub_check

GATE_WORD = re.compile(r"\bgat(?:e|es|ed|ing)\b", re.IGNORECASE)


def _docstring_node_ids(tree: ast.AST) -> set[int]:
    ids = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            first = node.body[0] if node.body else None
            if (isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant)
                    and isinstance(first.value.value, str)):
                ids.add(id(first.value))
    return ids


def _printable_strings() -> list[tuple[int, str]]:
    tree = ast.parse(PUB_CHECK.read_text(encoding="utf-8"))
    docstrings = _docstring_node_ids(tree)
    found = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Constant) and isinstance(node.value, str)
                and id(node) not in docstrings):
            found.append((node.lineno, node.value))
        elif isinstance(node, ast.keyword) and node.arg:
            # observe(gate=...) prints "gate: ..." in the report's value column.
            found.append((node.value.lineno, node.arg))
    return found


def test_scan_actually_sees_the_messages():
    """Precondition: the scan must see real messages, or a pass means nothing."""
    strings = [s for _, s in _printable_strings()]
    assert len(strings) > 4000, f"scan saw only {len(strings)} strings"
    # A known finding message, a known observe() key, and a known registry field.
    assert any("which is not in the package; it 404s on publication" in s for s in strings)
    # observe() keyword names are scanned too (they print as "key: value").
    assert any(s == "relative_refs_checked" for s in strings)
    assert any("compares_to" == s for s in strings)


def test_no_printable_string_uses_gate_wording():
    bad = [(line, s) for line, s in _printable_strings() if GATE_WORD.search(s)]
    assert not bad, (
        "pub-check prints text that uses 'gate', 'gated' or 'gating'; say "
        "'checked against' or 'check' instead:\n"
        + "\n".join(f"  line {line}: {s}" for line, s in bad)
    )


def test_no_registry_entry_uses_gate_wording():
    inventory = oasis_pub_check.conditions_inventory()
    assert len(inventory) > 100, f"registry has only {len(inventory)} conditions"
    bad = [(c["check"], k, v) for c in inventory for k, v in c.items()
           if isinstance(v, str) and GATE_WORD.search(v)]
    assert not bad, (
        "the condition registry (--list-checks, CHECKS.md, validation report) "
        "uses gate wording:\n" + "\n".join(f"  {c} [{k}]: {v}" for c, k, v in bad)
    )
