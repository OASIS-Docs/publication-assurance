#!/usr/bin/env python3
# Copyright 2026 OASIS Open
# SPDX-License-Identifier: Apache-2.0
# Authored by Michael Coletta, Technical Advisor to OASIS Open.
"""Verify a rendered PDF against the published PDF of the same specification.

verify_md.py compares HTML, where a table of contents has no page numbers on
either side. A PDF's contents do, and the DMLex Markdown edition's first
renders had none against the published standard's 133: no HTML comparison
could see it. This compares the two PDFs' text, every page, the way
verify_md.py compares the HTML:

- Words. Both PDFs are read with pdftotext -layout; running header and
  footer lines are taken out, and the rest is aligned word by word with
  difflib. A difference that disappears once spaces and hyphens are removed
  is line wrapping (FOP hyphenates, Chrome breaks URLs at a hyphen) and is
  counted, not reported. List bullets are dropped: a renderer may draw them
  outside the text layer. Ligature glyphs (U+FB00 to U+FB06) are read as
  their letters.
- Reordering. A run of differences within 80 tokens of each other whose two
  sides hold the same characters in a different order (spaces and hyphens
  aside: pdftotext may join a label to its neighbour) is text laid out in another
  order (a caption beside a code block split over a page break, labels in a
  regenerated diagram); it is counted, not reported. A word that changed is
  still reported.
- Contents. Each contents entry's page number is read as a <page> token, so
  the numbers need not be equal (the two editions paginate differently) but
  an entry with a number on one side and none on the other is a difference.
- Running lines. A line near the top or bottom of the page that repeats,
  digits aside, on at least half the pages is a running header or footer.
  Each side's set of them is compared, and every page of the rendered PDF
  must carry one.

--allow takes verify_md.py's allow files ({"published", "markdown",
"reason"}, with "count" and "context"). {"kind": "footer", "published": ...,
"markdown": ...} accepts a running line, digits written as #. A rule that
accepted nothing fails the run.

What it cannot see: where a figure is drawn, what it looks like, and type
size (the gate's pdf-legibility and pdf-type-scale checks measure that). Use
render/compare.mjs and render/REVIEW.md for the pictures.

Usage: verify_pdf.py RENDERED.pdf PUBLISHED.pdf|URL [--allow FILE]... [--json OUT]
Exit 0 when every check passes, 1 when any fails, 2 when an input cannot be read.
"""
import argparse
import collections
import difflib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'pub-check'))
from verify_md import load_rules, tokens  # noqa: E402
from oasis_pub_check import _TOC_ENTRY, _TOC_NUMBER, _toc_title  # noqa: E402

PAGE = '<page>'
BULLETS = set('•◦▪■□●○‣∙')
EDGE = 3  # lines at the top and bottom of a page where a running line can be
CLUSTER = 80  # equal tokens that may separate the differences of one reordered run
LIGATURES = {0xFB00: 'ff', 0xFB01: 'fi', 0xFB02: 'fl', 0xFB03: 'ffi', 0xFB04: 'ffl', 0xFB05: 'st', 0xFB06: 'st'}


def fail(msg):
    print(f'verify_pdf: {msg}', file=sys.stderr)
    sys.exit(2)


def fetch(src, tmp):
    if not re.match(r'https?://', src):
        if not os.path.isfile(src):
            fail(f'cannot read {src}')
        return src
    path = os.path.join(tmp, 'published.pdf')
    req = urllib.request.Request(src, headers={'User-Agent': 'oasis-verify-pdf'})
    try:
        with urllib.request.urlopen(req, timeout=120) as r, open(path, 'wb') as f:
            f.write(r.read())
    except OSError as e:
        fail(f'cannot fetch {src}: {e}')
    return path


def pdf_pages(path):
    if not shutil.which('pdftotext'):
        fail('pdftotext (poppler) is not installed')
    r = subprocess.run(['pdftotext', '-layout', path, '-'], capture_output=True, text=True)
    if r.returncode != 0:
        fail(f'pdftotext cannot read {path}: {r.stderr.strip()}')
    pages = r.stdout.split('\f')
    if pages and not pages[-1].strip():
        pages.pop()
    return [[l for l in p.splitlines() if l.strip()] for p in pages]


def template(line):
    return re.sub(r'\d+', '#', re.sub(r'\s+', ' ', line).strip())


def running_lines(pages):
    """Templates of the lines that repeat near the page edges on half the pages or more."""
    seen = collections.Counter()
    for p in pages:
        seen.update({template(l) for l in p[:EDGE] + p[-EDGE:]})
    return {t for t, n in seen.items() if len(pages) >= 2 and n * 2 >= len(pages)}


def contents_lines(pages):
    """{(page, line index): line with its number}: the table of contents,
    found the way the gate's pdf-toc-pages check finds it."""
    out, started, seen = {}, False, set()
    for n, lines in enumerate(pages[:25]):
        head = next((i for i, l in enumerate(lines)
                     if re.fullmatch(r'\s*(?:Table of )?Contents\s*', l, re.I)), None)
        if not started and head is None:
            continue
        start = head + 1 if (head is not None and not started) else 0
        found = [i for i in range(start, len(lines)) if _TOC_ENTRY.match(lines[i])]
        titles = {_toc_title(lines[i]).lower() for i in found}
        if not found or titles & seen:
            break  # the body begins where its headings repeat the contents
        started = True
        seen |= titles
        for i in found:
            out[(n, i)] = lines[i]
        if len(found) < (len(lines) - start) // 3:
            break
    return out


def page_tokens(pages, running):
    """The document as one token stream, running lines out, contents numbers as <page>."""
    toc = contents_lines(pages)
    toks, pos = [], []
    for n, lines in enumerate(pages):
        for i, line in enumerate(lines):
            if (i < EDGE or i >= len(lines) - EDGE) and template(line) in running:
                continue
            if (n, i) in toc:
                has = bool(_TOC_NUMBER.search(line))
                t = tokens(_toc_title(line)) + ([PAGE] if has else [])
            elif (n, i - 1) in toc and not _TOC_NUMBER.search(toc[(n, i - 1)]) and _TOC_NUMBER.search(line):
                # a contents entry wrapped onto a second line carries its number there
                t = tokens(_toc_title(line)) + [PAGE]
            else:
                t = tokens(line.translate(LIGATURES))
            t = [x for x in t if x not in BULLETS]
            toks += t
            pos += [n + 1] * len(t)
    return toks, pos, sum(1 for l in toc.values() if _TOC_NUMBER.search(l)), len(toc)


def squash(ts):
    return ''.join(ts).replace('-', '')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('rendered', help='the PDF rendered from the edition being verified')
    ap.add_argument('published', help='the published PDF: a file or an http(s) URL')
    ap.add_argument('--allow', action='append', default=[],
                    help='JSON list of accepted deviations {published, markdown, reason}; may be repeated')
    ap.add_argument('--json', help='write the full report here')
    ap.add_argument('--context', type=int, default=8, help='tokens of context before each difference')
    a = ap.parse_args()
    rules = [r for path in a.allow for r in load_rules(path)]
    with tempfile.TemporaryDirectory() as tmp:
        pub_pages = pdf_pages(fetch(a.published, tmp))
    ren_pages = pdf_pages(a.rendered)
    pub_run, ren_run = running_lines(pub_pages), running_lines(ren_pages)
    A, apos, pub_toc_num, pub_toc = page_tokens(pub_pages, pub_run)
    B, bpos, ren_toc_num, ren_toc = page_tokens(ren_pages, ren_run)

    uses = {}
    text_rules = [(i, r) for i, r in enumerate(rules) if r.get('kind', 'text') == 'text']
    diffs, accepted = [], []
    sm = difflib.SequenceMatcher(None, A, B, autojunk=False)
    ops = [o for o in sm.get_opcodes() if o[0] != 'equal' and squash(A[o[1]:o[2]]) != squash(B[o[3]:o[4]])]
    wrapped = sum(1 for o in sm.get_opcodes() if o[0] != 'equal') - len(ops)
    runs, reordered = [], 0
    for o in ops:
        if runs and o[1] - runs[-1][-1][2] <= CLUSTER and o[3] - runs[-1][-1][4] <= CLUSTER:
            runs[-1].append(o)
        else:
            runs.append([o])
    kept = []
    for run in runs:
        i1, j1, i2, j2 = run[0][1], run[0][3], run[-1][2], run[-1][4]
        if len(run) > 1 and collections.Counter(squash(A[i1:i2])) == collections.Counter(squash(B[j1:j2])):
            reordered += 1
        else:
            kept += run
    for op, i1, i2, j1, j2 in kept:
        d = {'op': op, 'published': ' '.join(A[i1:i2]), 'markdown': ' '.join(B[j1:j2]),
             'context_before': ' '.join(A[max(0, i1 - a.context):i1]),
             'published_page': apos[min(i1, len(apos) - 1)] if apos else 0,
             'rendered_page': bpos[min(j1, len(bpos) - 1)] if bpos else 0}
        hit = next(((i, r) for i, r in text_rules
                    if r['published'] == d['published'] and r['markdown'] == d['markdown']
                    and d['context_before'].endswith(r.get('context', ''))
                    and uses.get(i, 0) < r.get('count', 1)), None)
        if hit:
            uses[hit[0]] = uses.get(hit[0], 0) + 1
            d['reason'] = hit[1]['reason']
            accepted.append(d)
        else:
            diffs.append(d)

    only_pub, only_ren = sorted(pub_run - ren_run), sorted(ren_run - pub_run)
    for i, r in enumerate(rules):
        if r.get('kind') == 'footer' and r['published'] in only_pub and r['markdown'] in only_ren:
            only_pub.remove(r['published'])
            only_ren.remove(r['markdown'])
            uses[i] = 1
    bare = [n + 1 for n, p in enumerate(ren_pages)
            if not any(template(l) in ren_run for l in p[:EDGE] + p[-EDGE:])] if ren_run else \
        list(range(1, len(ren_pages) + 1))

    empty = [side for side, toks in (('published', A), ('rendered', B)) if not toks]
    report = {
        'published_pages': len(pub_pages), 'rendered_pages': len(ren_pages),
        'published_tokens': len(A), 'rendered_tokens': len(B),
        'diff_regions': len(diffs), 'accepted_deviations': len(accepted), 'line_wrap_regions': wrapped, 'reordered_runs': reordered,
        'contents_entries_published': pub_toc, 'contents_numbered_published': pub_toc_num,
        'contents_entries_rendered': ren_toc, 'contents_numbered_rendered': ren_toc_num,
        'running_lines_published': sorted(pub_run), 'running_lines_rendered': sorted(ren_run),
        'running_lines_only_published': only_pub, 'running_lines_only_rendered': only_ren,
        'rendered_pages_without_running_line': bare, 'empty': empty,
        'allow_rules_unused': [r for i, r in enumerate(rules)
                               if i not in uses and r.get('kind', 'text') in ('text', 'footer')],
        'diffs': diffs, 'accepted': accepted,
    }
    if a.json:
        with open(a.json, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=1, ensure_ascii=False)
    for k, v in report.items():
        if k not in ('diffs', 'accepted', 'allow_rules_unused'):
            print(f'{k}: {v if not isinstance(v, list) else (len(v), v)}')
    for d in diffs:
        print(f"\n[{d['op']}] published p{d['published_page']}, rendered p{d['rendered_page']}: "
              f"...{d['context_before']}\n  PUB: {d['published']}\n  PDF: {d['markdown']}")
    for d in accepted:
        print(f"ACCEPTED: PUB[{d['published']}] PDF[{d['markdown']}] -- {d['reason']}")
    for r in report['allow_rules_unused']:
        print(f'UNUSED ALLOW RULE: {r}')
    ok = (not diffs and not only_pub and not only_ren and not bare and not empty
          and not report['allow_rules_unused'])
    print('\nRESULT:', 'PASS' if ok else 'FAIL')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
