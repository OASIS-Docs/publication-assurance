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
- the same scan runs over validation_report.py (the report's field labels, such
  as "Checker exit code", and its --help text) and publish_report.py (the job
  summary text);
- the scan covers pub-check's other printing modules (plain_language.py,
  tc_view.py, render_summary.py, advance_stage.py) and the first line of each
  module docstring, which five modules print as their --help description;
- the registry is also scanned through `conditions_inventory()`, the exact
  structure `--list-checks`, CHECKS.md and the validation report read.

What it deliberately does not scan: comments, docstrings beyond that first
line, and identifiers.
Those never reach a report. Code may say "gate" internally.
"""

from __future__ import annotations

import ast
import re

import pytest

from conftest import PUB_CHECK, oasis_pub_check

# Not preceded or followed by a letter, so snake_case ("gate_exit_code") is caught
# while "navigate", "aggregate" and "gateway" are not.
GATE_WORD = re.compile(r"(?<![A-Za-z])gat(?:e|es|ed|ing)(?![A-Za-z])", re.IGNORECASE)


def _docstring_node_ids(tree: ast.AST) -> set[int]:
    ids = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            first = node.body[0] if node.body else None
            if (isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant)
                    and isinstance(first.value.value, str)):
                ids.add(id(first.value))
    return ids


PRINTING_FILES = [PUB_CHECK] + [PUB_CHECK.parent / n for n in (
    "validation_report.py", "publish_report.py", "plain_language.py",
    "tc_view.py", "render_summary.py", "advance_stage.py")]


def _printable_strings(path=PUB_CHECK) -> list[tuple[int, str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    docstrings = _docstring_node_ids(tree)
    found = []
    # Five modules pass the first docstring line to argparse as the --help
    # description (`__doc__.splitlines()[0]`), so that line is printed.
    doc = ast.get_docstring(tree)
    if doc:
        found.append((1, doc.splitlines()[0]))
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


def test_report_files_scan_sees_their_labels():
    """Precondition for the report-file scan: it must see the real labels."""
    seen = [s for _, s in _printable_strings(PUB_CHECK.parent / "validation_report.py")]
    assert "Checker exit code" in seen, "validation_report.py scan missed its exit-code label"
    assert "Validation date" in seen
    summary = [s for _, s in _printable_strings(PUB_CHECK.parent / "publish_report.py")]
    assert any("produced no readable --json report" in s for s in summary)


# Minimum string counts per module: a precondition so an emptied or mis-parsed
# scan cannot pass. Measured 15 Oct 2026; set well below the measured counts.
MIN_STRINGS = {"oasis_pub_check.py": 4000, "validation_report.py": 150,
               "publish_report.py": 100, "plain_language.py": 100,
               "tc_view.py": 100, "render_summary.py": 30, "advance_stage.py": 60}


@pytest.mark.parametrize("path", PRINTING_FILES, ids=lambda p: p.name)
def test_every_scanned_module_yields_strings(path):
    strings = _printable_strings(path)
    assert len(strings) > MIN_STRINGS[path.name], f"{path.name}: scan saw only {len(strings)} strings"


@pytest.mark.parametrize("name", ["advance_stage.py", "oasis_pub_check.py", "publish_report.py",
                                  "tc_view.py", "validation_report.py"])
def test_help_description_line_is_scanned(name):
    """These modules print the first docstring line as their --help description."""
    path = PUB_CHECK.parent / name
    first = ast.get_docstring(ast.parse(path.read_text(encoding="utf-8"))).splitlines()[0]
    assert first in [s for _, s in _printable_strings(path)]


@pytest.mark.parametrize("path", PRINTING_FILES, ids=lambda p: p.name)
def test_no_printable_string_uses_gate_wording(path):
    bad = [(line, s) for line, s in _printable_strings(path) if GATE_WORD.search(s)]
    assert not bad, (
        f"{path.name} prints text that uses 'gate', 'gated' or 'gating'; say "
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
