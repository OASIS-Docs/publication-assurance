#!/usr/bin/env python3
# Copyright 2026 OASIS Open
# SPDX-License-Identifier: Apache-2.0
# Authored by Michael Coletta, Technical Advisor to OASIS Open.
"""Side-by-side page pairs for a vision review, with a planted fault.

verify/verify_pdf.py reads every word of both PDFs. What it cannot read is
how a page looks: a figure off the page, a number on the wrong line, a
caption beside the wrong block. That needs eyes, and eyes asked "do these
match?" answer yes: the first DMLex comparison looked at the contents page
and passed it with no page numbers. So this tool makes the review a task
that cannot be passed by glancing:

  make   Pair each sampled page of the rendered PDF with the published page
         that shares most of its words (the two paginate differently), and
         write each pair as one image, published on the left. Every page
         with a figure or an image, the cover and the contents are taken,
         plus --sample random pages. One extra pair is a planted fault: a
         real pair with something erased from its right side. Which pair,
         and what was erased, goes to --key, which the reviewer must not
         be able to read. PROMPT.md, written beside the pairs, is the brief.
  grade  Read the reviewer's JSON (the shape PROMPT.md asks for). Every
         copied line is looked up in the text of the page it claims to come
         from: a reviewer that did not look writes lines that are not there
         (the first Haiku run on DMLex "copied" NVH node text from the
         contents page). The planted fault counts as found only when a
         difference on its pair names what was erased. Exit 0 only when
         every pair's lines are on its pages and the fault was named. The
         other pairs' differences are printed for a person to rule on.

A reviewer that misses the planted fault has not reviewed the pages; its
"no differences" on the rest is worth nothing, and the review is run again.

Requirements: poppler (pdftotext, pdftoppm, pdfimages, pdfinfo) and Pillow.

Usage: review_pairs.py make RENDERED.pdf PUBLISHED.pdf OUT_DIR --key KEY.json [--sample N] [--seed S] [--dpi D] [--plant KIND]
       review_pairs.py grade KEY.json REVIEW.json [RERUN.json...]
"""
import argparse
import json
import os
import random
import re
import subprocess
import sys

try:
    from PIL import Image, ImageDraw
except ImportError:  # grade needs no images
    Image = ImageDraw = None

MIN_LINES = 5  # lines the brief asks a reviewer to copy from each side of a pair
MIN_EVIDENCE = 3  # of those, lines that must show the page was read (fewer if the page has fewer)
FOUND = 0.8  # share of a pair's copied lines that must be on its pages
NAMES = {  # what a reviewer who saw the planted fault says about it
    'right-column': r'page\s*num|numbers?\b|right[- ]hand|leader',
    'footer': r'footer|copyright|page\s+\S+\s+of|running',
    'text-lines': r'missing|blank|gap|erased|absent|white\s*space|empty',
}


def run(*cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f'review_pairs: {" ".join(cmd[:2])} failed: {r.stderr.strip()}')
    return r.stdout


def page_words(pdf):
    pages = run('pdftotext', '-layout', pdf, '-').split('\f')
    if pages and not pages[-1].strip():
        pages.pop()
    return [set(re.findall(r'[A-Za-z][A-Za-z0-9]{3,}', p)) for p in pages], pages


def match(ren, pub):
    """For each rendered page, a published page sharing its words, both taken
    in document order: the alignment that shares the most words overall, so
    a page of repeated table names cannot pair with one far away."""
    sim = [[len(r & p) / max(len(r | p), 1) for p in pub] for r in ren]
    best, back = [], []
    prev = [0.0] * len(pub)
    for i in range(len(ren)):
        run_max, arg, row, brow = -1.0, 0, [], []
        for j in range(len(pub)):
            if prev[j] > run_max:
                run_max, arg = prev[j], j
            row.append(sim[i][j] + run_max)
            brow.append(arg)
        best.append(row)
        back.append(brow)
        prev = row
    j = max(range(len(pub)), key=lambda k: prev[k])
    out = [0] * len(ren)
    for i in range(len(ren) - 1, -1, -1):
        out[i] = j
        j = back[i][j]
    return out


def figure_pages(pdf, texts):
    """Pages with a raster image, or with a figure caption."""
    pages = set()
    for line in run('pdfimages', '-list', pdf).splitlines()[2:]:
        f = line.split()
        if f and f[0].isdigit():
            pages.add(int(f[0]) - 1)
    for n, t in enumerate(texts):
        if re.search(r'^\s*(Figure|Fig\.)\s+\d', t, re.M):
            pages.add(n)
    return pages


def contents_pages(texts):
    out = []
    for n, t in enumerate(texts[:25]):
        if re.search(r'^\s*(Table of )?Contents\s*$', t, re.M | re.I) or (out and out[-1] == n - 1 and
                                                                        len(re.findall(r'\s\d+\s*$', t, re.M)) > 10):
            out.append(n)
    return out


def raster(pdf, page, dpi, path):
    stem = path[:-4]
    run('pdftoppm', '-r', str(dpi), '-png', '-singlefile', '-f', str(page + 1), '-l', str(page + 1), pdf, stem)
    return Image.open(path).convert('RGB')


def plant(img, kind):
    """Erase one thing a reader of the page would miss: the footer, the
    right-hand column (page numbers on a contents page, the end of lines
    elsewhere), or three lines of text."""
    w, h = img.size
    d = ImageDraw.Draw(img)
    if kind == 'footer':
        d.rectangle([0, int(h * 0.92), w, h], fill='white')
    elif kind == 'right-column':
        d.rectangle([int(w * 0.84), int(h * 0.06), w, int(h * 0.935)], fill='white')
    else:
        d.rectangle([0, int(h * 0.45), w, int(h * 0.52)], fill='white')
    return img


def make(a):
    if Image is None:
        sys.exit('review_pairs: make needs Pillow (pip install pillow)')
    rng = random.Random(a.seed)
    ren_words, ren_texts = page_words(a.rendered)
    pub_words, _ = page_words(a.published)
    partner = match(ren_words, pub_words)
    must = {0} | set(contents_pages(ren_texts)) | figure_pages(a.rendered, ren_texts)
    rest = [n for n in range(len(ren_words)) if n not in must]
    chosen = sorted(must | set(rng.sample(rest, min(a.sample, len(rest)))))
    os.makedirs(a.out, exist_ok=True)
    tmp = os.path.join(a.out, '.pages')
    os.makedirs(tmp, exist_ok=True)
    pairs = [{'rendered_page': n + 1, 'published_page': partner[n] + 1} for n in chosen]
    # The planted pair is a page not otherwise sampled, so it has no twin to
    # be told apart from; on a contents page the fault is its page numbers.
    toc = contents_pages(ren_texts)
    unused = [n for n in range(len(ren_words)) if n not in chosen]
    if a.plant == 'right-column' and toc:
        src = rng.choice(toc)
    else:
        src = rng.choice(unused or chosen)
    kind = a.plant or ('right-column' if src in toc else rng.choice(['footer', 'text-lines']))
    # Never also show the planted page untouched: a reviewer who meets it twice
    # can find the fault by comparing pairs, not by reading the page (the Sonnet
    # run on DMLex met the contents page twice and began doubting its own read).
    pairs = [p for p in pairs if p['rendered_page'] != src + 1]
    order = pairs + [{'rendered_page': src + 1, 'published_page': partner[src] + 1, 'planted': kind}]
    rng.shuffle(order)
    for k, p in enumerate(order, 1):
        left = raster(a.published, p['published_page'] - 1, a.dpi, os.path.join(tmp, 'l.png'))
        right = raster(a.rendered, p['rendered_page'] - 1, a.dpi, os.path.join(tmp, 'r.png'))
        if 'planted' in p:
            right = plant(right, p['planted'])
        h = max(left.height, right.height)
        img = Image.new('RGB', (left.width + right.width + 12, h), 'black')
        img.paste(left, (0, 0))
        img.paste(right, (left.width + 12, 0))
        p['pair'] = f'pair-{k:03d}.png'
        img.save(os.path.join(a.out, p['pair']))
    for f in os.listdir(tmp):
        os.remove(os.path.join(tmp, f))
    os.rmdir(tmp)
    canary = next(p for p in order if 'planted' in p)
    os.makedirs(os.path.dirname(os.path.abspath(a.key)), exist_ok=True)
    with open(a.key, 'w', encoding='utf-8') as f:
        json.dump({'pairs': order, 'planted_pair': canary['pair'], 'planted': canary['planted'],
                   'published': os.path.abspath(a.published), 'rendered': os.path.abspath(a.rendered)}, f, indent=1)
    names = [p['pair'] for p in order]
    with open(os.path.join(a.out, 'PROMPT.md'), 'w', encoding='utf-8') as f:
        f.write(PROMPT.format(n=len(names), min_lines=MIN_LINES, files='\n'.join(f'- {x}' for x in names)))
    print(f'{len(order)} pairs ({len(pairs)} sampled of {len(ren_words)} pages, 1 planted) in {a.out}; key in {a.key}')


PROMPT = """# Page review: published (left) against rendered (right)

Each image is one pair: a page of the published PDF on the left, a page of
the re-rendered edition on the right. The two editions paginate differently,
so the pages overlap in content but do not start and end at the same place.
Compare how the SAME content is shown on both sides.

Do not judge whether a pair "looks the same". Work through each pair in this
order and write down what you see before you decide anything:

1. Copy {min_lines} lines of the shared content from the LEFT page exactly as
   printed, including every number, dot leader, bullet or list letter. Choose
   lines with words in them, at least three of eight characters or more: a
   lone bracket, a page footer or a line on every page shows nothing. Then
   the same lines from the RIGHT page. Your lines are checked against the
   pages' text.
2. List every kind of element on each side: headings, list numbers or
   letters, page numbers in a contents list, dot leaders, header and footer
   fields (name, date, copyright, page x of y), captions, figures, tables,
   code blocks, rules, logos.
3. Report each kind of element that is on one side and not the other, and
   each line from step 1 that differs. A pair with no differences must still
   carry its copied lines.

Some pairs may have a deliberate fault. Treat every pair the same.

Answer with JSON only, a list with one object per pair:

[{{"pair": "pair-001.png",
   "left_lines": ["..."], "right_lines": ["..."],
   "only_left": ["..."], "only_right": ["..."],
   "differences": ["..."]}}]

The {n} pairs:
{files}
"""


def norm(s):
    return re.sub(r'[^0-9a-z]+', '', str(s).lower().replace('ﬁ', 'fi').replace('ﬂ', 'fl'))


def evidence(lines, generic):
    """The copied lines that can show the page was read: distinct, eight or
    more letters and digits, and not text that is on most pages (a footer's
    "OASIS Open", a running title). A line of "1" or "Copyright" proves nothing."""
    out = []
    for x in lines:
        n = norm(x)
        if len(n) >= 8 and n not in out and not any(re.sub(r'\d', '', n) in g for g in generic):
            out.append(n)
    return out


def generic_lines(pages):
    """Lines found on half the pages or more: they match any page."""
    seen = {}
    for p in pages:
        # digits out: a footer differs from page to page only by its page number
        for n in {re.sub(r'\d', '', norm(x)) for x in p.splitlines() if len(norm(x)) >= 8}:
            seen[n] = seen.get(n, 0) + 1
    return {n for n, k in seen.items() if k * 2 >= len(pages) and k > 1}


def grade(a):
    key = json.load(open(a.key, encoding='utf-8'))
    texts = {side: run('pdftotext', '-layout', key[side], '-').split('\f') for side in ('published', 'rendered')}
    page = lambda side, n: texts[side][n - 1] if 0 < n <= len(texts[side]) else ''
    generic = {side: generic_lines(texts[side]) for side in texts}
    by = {}
    for path in a.review:  # a later review of a pair (a re-run of the rejected ones) replaces an earlier
        try:
            review = json.load(open(path, encoding='utf-8'))
        except (OSError, ValueError) as e:
            sys.exit(f'review_pairs: cannot read the review {path}: {e}')
        by.update({r.get('pair'): r for r in review if isinstance(r, dict)})
    problems = []
    for p in key['pairs']:
        r = by.get(p['pair'])
        if r is None:
            problems.append(f"{p['pair']}: not answered")
            continue
        for side, pdf, n in (('left_lines', 'published', p['published_page']),
                             ('right_lines', 'rendered', p['rendered_page'])):
            copied = evidence(r.get(side) or [], generic[pdf])
            # a page that is mostly a figure has fewer lines to copy
            need = min(MIN_EVIDENCE, len(evidence(page(pdf, n).splitlines(), generic[pdf])))
            if len(copied) < need:
                problems.append(f"{p['pair']}: fewer than {need} {side} copied that show the page was read")
                continue
            flat = norm(page(pdf, n))
            there = sum(1 for x in copied if x in flat)
            if copied and there < FOUND * len(copied):
                problems.append(f"{p['pair']}: {len(copied) - there} of {len(copied)} {side} are not on "
                                f"{pdf} page {n}: not copied from the page")
    planted = by.get(key['planted_pair']) or {}
    says = lambda r: ' '.join(str(x) for k in ('differences', 'only_left', 'only_right') for x in r.get(k) or [])
    name = NAMES[key['planted']]
    # A word the reviewer writes about most pairs names nothing in particular.
    elsewhere = sum(1 for p in key['pairs'] if p['pair'] != key['planted_pair']
                    and re.search(name, says(by.get(p['pair']) or {}), re.I))
    caught = bool(re.search(name, says(planted), re.I)) and elsewhere * 4 <= len(key['pairs']) and not any(
        x.startswith(key['planted_pair'] + ':') for x in problems)
    print(f"planted fault: {key['planted_pair']} ({key['planted']}): {'FOUND' if caught else 'MISSED'}")
    for p in key['pairs']:
        r = by.get(p['pair']) or {}
        found = (r.get('differences') or []) + [f'only left: {x}' for x in r.get('only_left') or []] \
            + [f'only right: {x}' for x in r.get('only_right') or []]
        if found and p['pair'] != key['planted_pair']:
            print(f"\n{p['pair']} (published p{p['published_page']}, rendered p{p['rendered_page']}):")
            for x in found:
                print(f'  - {x}')
    for x in problems:
        print(f'INCOMPLETE: {x}')
    ok = caught and not problems
    print('\nREVIEW:', 'ACCEPTED' if ok else 'REJECTED (run the review again)')
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    m = sub.add_parser('make')
    m.add_argument('rendered')
    m.add_argument('published')
    m.add_argument('out')
    m.add_argument('--key', required=True, help='where the planted fault is recorded; keep it from the reviewer')
    m.add_argument('--sample', type=int, default=30, help='random pages beyond the cover, contents and figures')
    m.add_argument('--seed', type=int, default=None)
    m.add_argument('--dpi', type=int, default=100)
    m.add_argument('--plant', choices=('footer', 'right-column', 'text-lines'),
                   help='the fault to plant (default: chosen at random)')
    g = sub.add_parser('grade')
    g.add_argument('key')
    g.add_argument('review', nargs='+', help='the review, then any re-run of the pairs it failed')
    a = ap.parse_args()
    if a.cmd == 'make':
        out, keydir = os.path.realpath(a.out), os.path.realpath(os.path.dirname(os.path.abspath(a.key)))
        if os.path.commonpath([out, keydir]) == out:
            sys.exit('review_pairs: --key must be outside OUT_DIR, where the reviewer cannot read it')
        make(a)
        return 0
    return grade(a)


if __name__ == '__main__':
    sys.exit(main())
