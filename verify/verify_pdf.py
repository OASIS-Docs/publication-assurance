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
  difflib. Two things are counted, not reported, because they are how a
  renderer lays text out and not what the text says:
  - line wrapping: the two sides' tokens joined without spaces are equal,
    once a hyphen that ends a line between two letters (FOP hyphenates) is
    allowed to vanish. Any other hyphen, a minus sign among them, counts;
  - a moved block: three or more tokens deleted in one place and inserted,
    the same, within 400 tokens (a caption printed beside a code block that
    a page break split). A block that changed on the way is reported.
  List bullets are dropped (a renderer may draw them outside the text
  layer), and ligature glyphs (U+FB00 to U+FB06) are read as their letters.
- Contents. Each contents entry's page number is read as a <page> token, so
  the numbers need not be equal (the two editions paginate differently) but
  an entry with a number on one side and none on the other is a difference.
- Running lines. A line near the top or bottom of the page that repeats,
  digits aside, on at least half the pages is a running header or footer.
  Each is compared with its numbers kept, except those that change from page
  to page and the document's page count ("Page # of #"): a footer with the
  wrong version or date is a difference. Every rendered page must carry one.

--allow takes verify_md.py's allow files ({"published", "markdown",
"reason"}, with "count" and "context"). {"kind": "footer", "published": ...,
"markdown": ...} accepts a running line as the report prints it.
{"kind": "region", "from": ..., "to": ..., "reason": ...} names a stretch
after the contents, from the tokens "from" up to the tokens "to", whose
order is not the document's to keep (a diagram regenerated from the TC's
source lays its labels out anew): there the two sides must hold the same
characters, in any order. A rule that accepted nothing fails the run.

What it cannot see: where a figure is drawn, what it looks like, and type
size (the gate's pdf-legibility and pdf-type-scale checks measure that). Use
render/review_pairs.py for the pictures.

Usage: verify_pdf.py RENDERED.pdf PUBLISHED.pdf|URL [--allow FILE]... [--json OUT]
Exit 0 when every check passes, 1 when any fails, 2 when an input cannot be read.
"""
import argparse
import collections
import difflib
import itertools
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
MOVE = 400  # tokens a block may travel and still count as moved
MIN_MOVE = 3  # tokens in the smallest block that counts as moved
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
    """{template: the running line as compared}. A template is a line near the
    page edges, digits masked, on half the pages or more. It is compared with
    only the numbers masked that change from page to page or are the page
    count, so the version, date and year in a footer are compared."""
    seen = collections.defaultdict(list)
    for p in pages:
        for l in {re.sub(r'\s+', ' ', x).strip() for x in p[:EDGE] + p[-EDGE:]}:
            seen[template(l)].append(l)
    out = {}
    for t, lines in seen.items():
        if len(lines) < 2 or len(lines) * 2 < len(pages):
            continue  # a running line repeats: on two pages at least, and on half of them
        parts = [re.split(r'(\d+)', l) for l in lines]
        if len({len(p) for p in parts}) != 1:
            out[t] = t
            continue
        shown, varied = [], False
        for k, col in enumerate(zip(*parts)):
            if k % 2 == 0:
                shown.append(col[0])
                continue
            # the page count is masked only after the page number ("Page 3 of 194"),
            # so a "2" in "v2.0" is compared even in a two-page document
            varies = len(set(col)) > 1
            count = varied and col[0] == str(len(pages)) and len(set(col)) == 1
            shown.append('#' if varies or count else col[0])
            varied = varied or varies
        out[t] = ''.join(shown)
    return out


def contents_lines(pages):
    """{(page, line index): line}: the table of contents, found the way the
    gate's pdf-toc-pages check finds it."""
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


class Stream:
    """The document as one token stream: running lines out, contents numbers
    as <page>, each token's page, and which hyphens end a line mid-word."""

    def __init__(self, pages, running):
        toc = contents_lines(pages)
        self.toks, self.pos, self.soft = [], [], set()
        self.toc_entries = len(toc)
        self.toc_end = 0
        for n, lines in enumerate(pages):
            for i, line in enumerate(lines):
                if (i < EDGE or i >= len(lines) - EDGE) and template(line) in running:
                    continue
                if (n, i) in toc:
                    t = tokens(_toc_title(line)) + ([PAGE] if _TOC_NUMBER.search(line) else [])
                elif (n, i - 1) in toc and not _TOC_NUMBER.search(toc[(n, i - 1)]) and _TOC_NUMBER.search(line):
                    t = tokens(_toc_title(line)) + [PAGE]  # a wrapped entry carries its number on its last line
                else:
                    t = tokens(line.translate(LIGATURES))
                t = [x for x in t if x not in BULLETS]
                nxt = next((l for l in lines[i + 1:]), '')
                if len(t) >= 2 and t[-1] == '-' and t[-2][-1:].isalpha() and nxt.strip()[:1].isalpha():
                    self.soft.add(len(self.toks) + len(t) - 1)
                self.toks += t
                self.pos += [n + 1] * len(t)
                if (n, i) in toc:
                    self.toc_end = len(self.toks)

    @property
    def toc_numbered(self):
        return self.toks.count(PAGE)

    def joined(self, i1, i2):
        """The tokens without spaces, each line-end hyphen both kept and dropped."""
        soft = [k for k in range(i1, i2) if k in self.soft]
        out = set()
        for drop in itertools.product((False, True), repeat=min(len(soft), 6)):
            gone = {k for k, d in zip(soft, drop) if d}
            out.add(''.join(t for k, t in enumerate(self.toks[i1:i2], i1) if k not in gone))
        return out

    def find(self, words, start):
        want = tokens(words)
        for k in range(start, len(self.toks) - len(want) + 1):
            if self.toks[k:k + len(want)] == want:
                return k
        return None


def regions(A, B, rules, uses):
    """Cut each declared region out of both streams; a region whose two sides
    hold different characters stays a difference."""
    cut, findings = [], []
    for i, r in enumerate(rules):
        if r.get('kind') != 'region':
            continue
        spans = []
        for s in (A, B):
            a = s.find(r['from'], s.toc_end)
            b = s.find(r['to'], a + 1) if a is not None else None
            spans.append((a, b))
        if None in (x for sp in spans for x in sp):
            continue  # unused; reported as such
        (a1, a2), (b1, b2) = spans
        ca = collections.Counter(''.join(A.toks[a1:a2]).replace(' ', ''))
        cb = collections.Counter(''.join(B.toks[b1:b2]).replace(' ', ''))
        uses[i] = 1
        if ca != cb:
            findings.append({'op': 'region', 'published': f"{r['from']} .. {r['to']}: "
                             + ''.join(sorted((ca - cb).elements())),
                             'markdown': ''.join(sorted((cb - ca).elements())),
                             'context_before': '', 'published_page': A.pos[a1], 'rendered_page': B.pos[b1]})
        cut.append(((a1, a2), (b1, b2)))
    return cut, findings


def compare(pub_pages, ren_pages, rules, context=8):
    pub_run, ren_run = running_lines(pub_pages), running_lines(ren_pages)
    A, B = Stream(pub_pages, pub_run), Stream(ren_pages, ren_run)
    uses = {}
    cut, region_diffs = regions(A, B, rules, uses)
    skip_a = {k for (a1, a2), _ in cut for k in range(a1, a2)}
    skip_b = {k for _, (b1, b2) in cut for k in range(b1, b2)}
    ia = [k for k in range(len(A.toks)) if k not in skip_a]
    ib = [k for k in range(len(B.toks)) if k not in skip_b]
    ta, tb = [A.toks[k] for k in ia], [B.toks[k] for k in ib]

    sm = difflib.SequenceMatcher(None, ta, tb, autojunk=False)
    ops, wrapped = [], 0
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == 'equal':
            continue
        sa = A.joined(ia[i1], ia[i2 - 1] + 1) if i2 > i1 else {''}
        sb = B.joined(ib[j1], ib[j2 - 1] + 1) if j2 > j1 else {''}
        if sa & sb:
            wrapped += 1
        else:
            ops.append((op, i1, i2, j1, j2))

    # A block deleted in one place and inserted, unchanged, near by has moved.
    moved = set()
    for x, (_, i1, i2, j1, j2) in enumerate(ops):
        if i2 - i1 < MIN_MOVE or x in moved:
            continue
        for y, (_, k1, k2, l1, l2) in enumerate(ops):
            if y == x or y in moved or l2 - l1 != i2 - i1 or abs(k1 - i1) > MOVE:
                continue
            if ta[i1:i2] == tb[l1:l2] and j2 == j1 and k2 == k1:
                moved |= {x, y}
                break
    kept = [o for n, o in enumerate(ops) if n not in moved]

    text_rules = [(i, r) for i, r in enumerate(rules) if r.get('kind', 'text') == 'text']
    diffs, accepted = list(region_diffs), []
    for op, i1, i2, j1, j2 in kept:
        d = {'op': op, 'published': ' '.join(ta[i1:i2]), 'markdown': ' '.join(tb[j1:j2]),
             'context_before': ' '.join(ta[max(0, i1 - context):i1]),
             'published_page': A.pos[ia[min(i1, len(ia) - 1)]] if ia else 0,
             'rendered_page': B.pos[ib[min(j1, len(ib) - 1)]] if ib else 0}
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

    pub_lines, ren_lines = set(pub_run.values()), set(ren_run.values())
    only_pub, only_ren = sorted(pub_lines - ren_lines), sorted(ren_lines - pub_lines)
    for i, r in enumerate(rules):
        if r.get('kind') == 'footer' and r['published'] in only_pub and r['markdown'] in only_ren:
            only_pub.remove(r['published'])
            only_ren.remove(r['markdown'])
            uses[i] = 1
    bare = [n + 1 for n, p in enumerate(ren_pages)
            if not any(template(l) in ren_run for l in p[:EDGE] + p[-EDGE:])]

    return {
        'published_pages': len(pub_pages), 'rendered_pages': len(ren_pages),
        'published_tokens': len(A.toks), 'rendered_tokens': len(B.toks),
        'diff_regions': len(diffs), 'accepted_deviations': len(accepted),
        'line_wrap_regions': wrapped, 'moved_blocks': len(moved) // 2, 'regions_compared': len(cut),
        'contents_entries_published': A.toc_entries, 'contents_numbered_published': A.toc_numbered,
        'contents_entries_rendered': B.toc_entries, 'contents_numbered_rendered': B.toc_numbered,
        'running_lines_published': sorted(pub_lines), 'running_lines_rendered': sorted(ren_lines),
        'running_lines_only_published': only_pub, 'running_lines_only_rendered': only_ren,
        'rendered_pages_without_running_line': bare,
        'empty': [side for side, s in (('published', A), ('rendered', B)) if not s.toks],
        'allow_rules_unused': [r for i, r in enumerate(rules)
                               if i not in uses and r.get('kind', 'text') in ('text', 'footer', 'region')],
        'diffs': diffs, 'accepted': accepted,
    }


def passed(report):
    return not (report['diffs'] or report['running_lines_only_published'] or report['running_lines_only_rendered']
                or report['rendered_pages_without_running_line'] or report['empty'] or report['allow_rules_unused'])


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
    report = compare(pub_pages, pdf_pages(a.rendered), rules, a.context)
    if a.json:
        with open(a.json, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=1, ensure_ascii=False)
    for k, v in report.items():
        if k not in ('diffs', 'accepted', 'allow_rules_unused'):
            print(f'{k}: {v if not isinstance(v, list) else (len(v), v)}')
    for d in report['diffs']:
        print(f"\n[{d['op']}] published p{d['published_page']}, rendered p{d['rendered_page']}: "
              f"...{d['context_before']}\n  PUB: {d['published']}\n  PDF: {d['markdown']}")
    for d in report['accepted']:
        print(f"ACCEPTED: PUB[{d['published']}] PDF[{d['markdown']}] -- {d['reason']}")
    for r in report['allow_rules_unused']:
        print(f'UNUSED ALLOW RULE: {r}')
    ok = passed(report)
    print('\nRESULT:', 'PASS' if ok else 'FAIL')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
