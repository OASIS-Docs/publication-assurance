#!/usr/bin/env python3
# Copyright 2026 OASIS Open
# SPDX-License-Identifier: Apache-2.0
# Authored by Michael Coletta, Technical Advisor to OASIS Open.
"""Append a GitHub Step Summary section from an oasis_pub_check.py --json report.

Used by action.yml's "Write step summary" step so a TC member who opens a
run page sees the outcome first and what to fix next: the target, the one-line
outcome ("Publishable" or "Not publishable: N blockers, M warnings"), a table
of the blockers and a collapsed table of the warnings, each row giving where
the problem is, what is wrong in plain English and how to fix it (tc_view.py),
then the full ordered findings list in a collapsible fenced block, and -- when --report-dir
is given -- one plain sentence saying where the full report files are: the
folder the workflow writes, listed under Artifacts on the run page when the
workflow uploads it.

Usage:
  render_summary.py <report.json> [--txt <report.txt>] [--title <label>]
                     [--report-dir <dir>] [--package-dir <stage dir>]

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
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tc_view import outcome_md, rows  # noqa: E402
from validation_report import md_code, md_text  # noqa: E402


def build_section(report: dict, title: str, txt_body: str | None,
                   report_dir: str | None, package_dir: str | None = None) -> str:
    findings = report.get("findings", [])
    label = title or report.get("target", "package")

    lines = [
        f"## OASIS publication checks: {md_text(label)}",
        "",
        f"Target: {md_code(report.get('target', ''))}",
        "",
        outcome_md(findings, rows(findings, package_dir)),
    ]
    if txt_body:
        # Findings quote package text: the fence must outlast any backtick
        # run in it, or a quoted ``` would end the block and render the rest.
        run = max((len(m) for m in re.findall(r"`+", txt_body)), default=0)
        fence = "`" * max(3, run + 1)
        lines += [
            "<details>",
            "<summary>Full findings list (ordered)</summary>",
            "",
            fence,
            txt_body.rstrip("\n"),
            fence,
            "",
            "</details>",
            "",
        ]
    if report_dir:
        lines += [
            f"**Full report files:** the workflow writes them to the {md_code(report_dir)} "
            "folder. When it uploads that folder, it is listed under **Artifacts** at the "
            "bottom of this run's page, ready to download.",
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
    ap.add_argument("--report-dir", default=None,
                     help="directory the caller wrote pubcheck-report.txt/.json into "
                          "(action.yml's report-dir input); if given, the summary "
                          "section states these paths so a caller who forgets to "
                          "upload them as an artifact is still told where they are")
    ap.add_argument("--package-dir", default=None,
                     help="the checked stage directory, so each finding can name its file "
                          "and line; omit it for a zip target")
    args = ap.parse_args()

    with open(args.report_json) as f:
        report = json.load(f)

    txt_body = None
    if args.txt and os.path.isfile(args.txt):
        with open(args.txt) as f:
            txt_body = f.read()

    section = build_section(report, args.title, txt_body, args.report_dir, args.package_dir)

    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a") as f:
            f.write(section + "\n")
    else:
        print(section)

    return 0


if __name__ == "__main__":
    sys.exit(main())
