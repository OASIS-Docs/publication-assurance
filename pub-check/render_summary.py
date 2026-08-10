#!/usr/bin/env python3
# Copyright 2026 OASIS Open
# SPDX-License-Identifier: Apache-2.0
# Authored by Michael Coletta, Technical Advisor to OASIS Open.
"""Append a GitHub Step Summary section from an oasis_pub_check.py --json report.

Used by action.yml's "Write step summary" step so a TC member who opens a
run page sees the actual findings without opening raw logs: the target, the
verdict line (N blockers / N warnings -> PUBLISHABLE or NOT), and the full
ordered findings list in a collapsible fenced block.

Usage:
  render_summary.py <report.json> [--txt <report.txt>] [--title <label>]

Reads $GITHUB_STEP_SUMMARY from the environment and appends to it (creating
it if absent, matching the file GitHub Actions provides at runtime). Exits 0
on a missing/unset $GITHUB_STEP_SUMMARY (local/manual invocation) after
printing the section to stdout instead, so this script is also usable
outside a workflow for a quick look.
"""
from __future__ import annotations

import argparse
import json
import os
import sys


def build_section(report: dict, title: str, txt_body: str | None) -> str:
    findings = report.get("findings", [])
    blockers = sum(1 for f in findings if f.get("severity") == "BLOCKER")
    warnings = sum(1 for f in findings if f.get("severity") == "WARN")
    infos = sum(1 for f in findings if f.get("severity") == "INFO")
    verdict = "NOT PUBLISHABLE" if blockers else "PUBLISHABLE"
    label = title or report.get("target", "package")

    lines = [
        f"## pub-check: {label}",
        "",
        f"Target: `{report.get('target', '')}`",
        "",
        f"**{blockers} blocker(s), {warnings} warning(s), {infos} info "
        f"-> {verdict}**",
        "",
    ]
    if txt_body:
        lines += [
            "<details>",
            "<summary>Full findings list (ordered)</summary>",
            "",
            "```",
            txt_body.rstrip("\n"),
            "```",
            "",
            "</details>",
            "",
        ]
    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("report_json", help="path to the --json report file")
    ap.add_argument("--txt", default=None,
                     help="path to the matching human-readable (non --json) report; "
                          "included as a collapsible fenced block if given")
    ap.add_argument("--title", default="",
                     help="label for the summary heading; defaults to the report's "
                          "own target field (use this when calling the action more "
                          "than once, e.g. in a matrix, to distinguish the sections)")
    args = ap.parse_args()

    with open(args.report_json) as f:
        report = json.load(f)

    txt_body = None
    if args.txt and os.path.isfile(args.txt):
        with open(args.txt) as f:
            txt_body = f.read()

    section = build_section(report, args.title, txt_body)

    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a") as f:
            f.write(section + "\n")
    else:
        print(section)

    return 0


if __name__ == "__main__":
    sys.exit(main())
