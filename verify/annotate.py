#!/usr/bin/env python3
# Copyright 2026 OASIS Open
# SPDX-License-Identifier: Apache-2.0
# Authored by Michael Coletta, Technical Advisor to OASIS Open.
"""One line a reader of a GitHub Actions run sees: a verifier's verdict.

Reads a verify_md.py or verify_pdf.py --json report and prints a GitHub
annotation: a notice when it passed, an error naming what failed when it did
not. The run page shows annotations to everyone who can open it; a step's
log needs a sign-in.

Usage: annotate.py html|pdf REPORT.json
"""
import json
import sys


def html(r):
    ok = not (r['diffs'] or r['headings_missing'] or r['code_blocks_differing'] or r['allow_rules_unused']
              or r['list_numbering_published'] != r['list_numbering_markdown'] or r.get('contents_differing')
              or r['list_items_published'] != r['list_items_markdown'] or r['empty'])
    facts = (f"{r['published_tokens']:,} words and marks in order, {len(r['diffs'])} unexplained differences, "
             f"{r['accepted_deviations']} accepted; {r['code_blocks_published']} code blocks, "
             f"{len(r['code_blocks_differing'])} differing; list numbering "
             f"{'matches' if r['list_numbering_published'] == r['list_numbering_markdown'] else 'DIFFERS'}; "
             f"{r['contents_entries_markdown']} of {r['contents_entries_published']} contents entries")
    return ok, 'The HTML matches the published HTML' if ok else 'The HTML differs from the published HTML', facts


def pdf(r):
    ok = not (r['diffs'] or r['running_lines_only_published'] or r['running_lines_only_rendered']
              or r['rendered_pages_without_running_line'] or r['empty'] or r['allow_rules_unused'])
    facts = (f"{r['published_tokens']:,} words and marks in order, {len(r['diffs'])} unexplained differences, "
             f"{r['accepted_deviations']} accepted; contents entries numbered: {r['contents_numbered_rendered']} "
             f"of {r['contents_entries_rendered']} (published {r['contents_numbered_published']}); "
             f"footer missing on {len(r['rendered_pages_without_running_line'])} of {r['rendered_pages']} pages")
    return ok, 'The PDF matches the published PDF' if ok else 'The PDF differs from the published PDF', facts


def main():
    if len(sys.argv) != 3 or sys.argv[1] not in ('html', 'pdf'):
        sys.exit(__doc__)
    report = json.load(open(sys.argv[2], encoding='utf-8'))
    ok, title, facts = (html if sys.argv[1] == 'html' else pdf)(report)
    print(f"::{'notice' if ok else 'error'} title={title}::{facts}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
