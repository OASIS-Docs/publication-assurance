#!/usr/bin/env python3
# Copyright 2026 OASIS Open
# SPDX-License-Identifier: Apache-2.0
# Authored by Michael Coletta, Technical Advisor to OASIS Open.
"""Verify a Markdown edition of a specification against its published HTML.

Both sides are reduced to their visible text: the Markdown through pandoc
(GFM to HTML), the published HTML by stripping tags. Each becomes a sequence
of normalised tokens and difflib aligns them. Every region where the two
disagree is reported in full with context, so a reviewer sees exactly which
words the conversion dropped, added or changed.

Structure is checked independently of the text:
- every numbered heading in the published HTML appears in the Markdown, in order;
- every internal link (#id) in the Markdown has an anchor;
- the code blocks (<pre>) match in number and, in document order, byte for
  byte apart from whitespace at the ends of lines;
- every image the Markdown references exists under --root, and the image
  counts match.

The published HTML may be a file or an http(s) URL. docs.oasis-open.org is
served through Cloudflare, which can replace an email address with a
placeholder; the address is decoded before comparison, so a live URL and a
saved copy give the same result.

--allow names a JSON list of accepted deviations, each
{"published": ..., "markdown": ..., "reason": ...}, matched exactly against a
difference region's text. A rule accepts one difference unless it says
"count": N, and with "context": "..." only a difference whose preceding
tokens end with that text. {"kind": "heading", "published": ...} accepts a
published heading that the Markdown words differently. A rule without a
reason is refused; a rule that accepted nothing fails the run.
{"kind": "link", "published": URL or "", "markdown": URL or ""} accepts a
difference in the external link targets.

Tables and lists are compared by shape: the number of list items, and the
number of data tables (two or more rows, two or more cells in a row) with
their row and cell counts. A table flattened into paragraphs keeps its words
and loses its shape, so the word comparison alone would pass it.

Images are compared as rendered, source by source in order; external link
targets as a set; struck-through and hidden markup by count.

Usage: verify_md.py SPEC.md PUBLISHED.html|URL [--root DIR] [--allow FILE] [--json OUT]
Exit 0 when every check passes, 1 when any fails, 2 when the input cannot be read.
"""
import argparse
import difflib
import html
import json
import os
import re
import subprocess
import sys
import urllib.request


def cf_decode(hexstr):
    """Decode a Cloudflare email-obfuscation payload (first byte is the XOR key)."""
    b = bytes.fromhex(hexstr)
    return bytes(x ^ b[0] for x in b[1:]).decode('utf-8', errors='replace')


def html_text(s):
    s = re.sub(r'<span class="__cf_email__" data-cfemail="([0-9a-fA-F]+)">.*?</span>',
               lambda m: cf_decode(m.group(1)), s, flags=re.S)
    s = re.sub(r'<!--.*?-->', ' ', s, flags=re.S)
    s = re.sub(r'<(script|style|head)\b[^>]*>.*?</\1>', ' ', s, flags=re.S | re.I)
    s = re.sub(r'<[^>]+>', ' ', s)
    return html.unescape(s)


def tokens(text):
    text = text.replace(' ', ' ')
    text = re.sub('[“”„″]', '"', text)
    text = re.sub('[‘’′]', "'", text)
    text = re.sub('[–—]', '-', text)
    return re.findall(r"[A-Za-z0-9À-ɏ]+|[^\sA-Za-z0-9À-ɏ]", text)


def pandoc_version():
    try:
        r = subprocess.run(['pandoc', '--version'], capture_output=True, text=True)
    except FileNotFoundError:
        fail('pandoc is not installed; pandoc 3.x is required')
    v = r.stdout.split('\n', 1)[0].split()[-1]
    if int(v.split('.')[0]) < 3:
        fail(f'pandoc {v} found; pandoc 3.x is required (older releases parse GFM differently)')
    return v


def balanced_end(h, start, tag):
    """The end of the element opened at h[start], counting nested <tag>s."""
    depth = 0
    for t in re.finditer(rf'<(/?){tag}\b[^>]*>', h[start:], re.I):
        depth += -1 if t.group(1) else 1
        if depth == 0:
            return start + t.end()
    return None


def strip_toc(h):
    """Remove a generated table of contents and nothing else: the DocBook
    stylesheet's div.toc, or the OASIS Markdown template's "Table of Contents"
    heading and the one list after it. Anything else near them is compared."""
    m = re.search(r'<div class="toc">', h)
    if m:
        end = balanced_end(h, m.start(), 'div')
        if end:
            return h[:m.start()] + ' ' + h[end:]
    m = re.search(r'<h1[^>]*>Table of Contents</h1>\s*', h)
    if m:
        ul = re.match(r'<ul\b', h[m.end():])
        end = balanced_end(h, m.end(), 'ul') if ul else m.end()
        return h[:m.start()] + ' ' + h[end or m.end():]
    return h


def shapes(h):
    """List items, and each data table (two or more rows, two or more cells
    in a row) as its rows of cell text, so a word moved to another row or a
    table flattened into paragraphs is seen."""
    tables = []
    for m in re.finditer(r'<table\b[^>]*>(.*?)</table>', h, re.S | re.I):
        rows = [[' '.join(tokens(html_text(c)))
                 for c in re.findall(r'<t[dh]\b[^>]*>(.*?)</t[dh]>', r, re.S | re.I)]
                for r in re.findall(r'<tr\b[^>]*>(.*?)</tr>', m.group(1), re.S | re.I)]
        if len(rows) >= 2 and max(map(len, rows)) >= 2:
            tables.append(rows)
    return len(re.findall(r'<li[\s>]', h, re.I)), tables


def hidden(h):
    """Struck-through or hidden text still has its words; count the markup."""
    return len(re.findall(r'<(del|s|strike)\b|display\s*:\s*none|visibility\s*:\s*hidden', h, re.I))


def external_links(h):
    """Every http(s) link target, the scheme read as https (docs.oasis-open.org
    serves both, and the published HTML mixes them)."""
    return sorted(re.sub(r'^http://', 'https://', html.unescape(u))
                  for u in re.findall(r'<a\b[^>]*href="(https?://[^"]+)"', h, re.I))


def md_to_html(md_path):
    try:
        r = subprocess.run(['pandoc', '--preserve-tabs', '-f', 'gfm', '-t', 'html', md_path],
                           capture_output=True, text=True)
    except FileNotFoundError:
        fail('pandoc is not installed; pandoc 3.x is required')
    if r.returncode != 0:
        fail(f'pandoc failed: {r.stderr}')
    return r.stdout


def fail(msg):
    print(f'verify_md: {msg}', file=sys.stderr)
    sys.exit(2)


def read_published(src):
    if re.match(r'https?://', src):
        req = urllib.request.Request(src, headers={'User-Agent': 'oasis-verify-md'})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                raw = r.read()
        except OSError as e:
            fail(f'cannot fetch {src}: {e}')
        header = r.headers.get_content_charset()
    else:
        try:
            raw = open(src, 'rb').read()
        except OSError as e:
            fail(f'cannot read {src}: {e}')
        header = None
    head = raw[:raw.lower().find(b'</head>')] if b'</head>' in raw.lower() else raw[:8192]
    m = re.search(rb'charset=["\']?([\w-]+)', head)
    charset = header or (m.group(1).decode() if m else None)
    if charset:
        try:
            return raw.decode(charset, errors='replace')
        except LookupError:
            fail(f'{src} declares an unknown charset {charset!r}')
    try:
        return raw.decode('utf-8')
    except UnicodeDecodeError:
        return raw.decode('windows-1252', errors='replace')  # the HTML default without a declaration


def load_rules(path):
    try:
        rules = json.load(open(path, encoding='utf-8'))
    except (OSError, ValueError) as e:
        fail(f'cannot read allow file {path}: {e}')
    for i, r in enumerate(rules):
        if not isinstance(r, dict) or not str(r.get('reason', '')).strip():
            fail(f'allow rule {i} in {path} has no reason: {r}')
        if r.get('kind', 'text') not in ('text', 'heading', 'link'):
            fail(f'allow rule {i} in {path} has an unknown kind: {r}')
        if 'published' not in r or ('markdown' not in r and r.get('kind') != 'heading'):
            fail(f'allow rule {i} in {path} needs "published" and "markdown": {r}')
        if not isinstance(r.get('count', 1), int) or r.get('count', 1) < 1:
            fail(f'allow rule {i} in {path} has a count that is not a positive integer: {r}')
    return rules


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('md')
    ap.add_argument('html', help='the published HTML: a file or an http(s) URL')
    ap.add_argument('--root', default=None, help='the directory image paths are relative to '
                    '(default: the Markdown file\'s directory)')
    ap.add_argument('--json', help='write the full report here')
    ap.add_argument('--context', type=int, default=8, help='tokens of context before each difference')
    ap.add_argument('--allow', help='JSON list of accepted deviations {published, markdown, reason}')
    a = ap.parse_args()

    try:
        md_src = open(a.md, encoding='utf-8').read()
    except OSError as e:
        fail(f'cannot read {a.md}: {e}')
    root = a.root or os.path.dirname(os.path.abspath(a.md))
    rules = load_rules(a.allow) if a.allow else []
    pandoc = pandoc_version()
    pub = read_published(a.html)
    md_html = md_to_html(a.md)

    # Tables of contents are generated, not content: drop them from both sides.
    pub_body = strip_toc(pub)
    md_body = strip_toc(md_html)

    A = tokens(html_text(pub_body))
    B = tokens(html_text(md_body))
    sm = difflib.SequenceMatcher(None, A, B, autojunk=False)
    diffs = []
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == 'equal':
            continue
        diffs.append({'op': op, 'published': ' '.join(A[i1:i2]), 'markdown': ' '.join(B[j1:j2]),
                      'context_before': ' '.join(A[max(0, i1 - a.context):i1]), 'pub_pos': i1})
    accepted, keep, uses = [], [], {}
    text_rules = [(i, r) for i, r in enumerate(rules) if r.get('kind', 'text') == 'text']
    for d in diffs:
        hit = next(((i, r) for i, r in text_rules
                    if r['published'] == d['published'] and r['markdown'] == d['markdown']
                    and d['context_before'].endswith(r.get('context', ''))
                    and uses.get(i, 0) < r.get('count', 1)), None)
        if hit:
            uses[hit[0]] = uses.get(hit[0], 0) + 1
            d['reason'] = hit[1]['reason']
            accepted.append(d)
        else:
            keep.append(d)
    diffs = keep
    allowed_heads = {r['published']: i for i, r in enumerate(rules) if r.get('kind') == 'heading'}
    matched = sum(b.size for b in sm.get_matching_blocks())
    ratio = matched / max(len(A), 1)

    # Headings: every numbered published heading, in order.
    def heads(h):
        return [re.sub(r'\s+', ' ', html.unescape(re.sub('<[^>]+>', '', t))).strip()
                for _, t in re.findall(r'<h([1-6])[^>]*>(.*?)</h\1>', h, re.S)]
    pub_heads = [h for h in heads(pub) if re.match(r'^(\d+(\.\d+)*|Appendix [A-Z]|[A-Z](\.\d+)+) ', h)]
    norm = lambda h: ' '.join(tokens(re.sub(r'^(\d+)\.(\s)', r'\1\2',
                                            re.sub(r'^Appendix ([A-Z])\.', r'Appendix \1', h)))).lower()
    md_norm = [norm(h) for h in heads(md_html)]
    missing_heads, pos = [], 0
    for h in pub_heads:
        try:
            pos = md_norm.index(norm(h), pos) + 1
        except ValueError:
            if h in allowed_heads:
                uses[allowed_heads[h]] = 1
            else:
                missing_heads.append(h)

    # Anchors and internal links.
    anchors = set(re.findall(r"""id=['"]([^'"]+)['"]""", md_html))
    links = re.findall(r'href="#([^"]+)"', md_html)
    broken = sorted({l for l in links if l not in anchors})

    # Code blocks, in document order: blank lines around a block and
    # whitespace at line ends ignored, indentation kept. Aligned as sequences,
    # so one missing block is reported once, not as every block after it.
    def pres(h):
        out = []
        for m in re.finditer(r'<pre[^>]*>(.*?)</pre>', h, re.S):
            t = html.unescape(re.sub(r'<[^>]+>', '', m.group(1)))
            out.append('\n'.join(l.rstrip() for l in t.split('\n')).strip('\n'))
        return out
    P, M = pres(pub), pres(md_html)
    code_mismatch = []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, P, M, autojunk=False).get_opcodes():
        if op != 'equal':
            code_mismatch.append({'op': op, 'published_blocks': list(range(i1, i2)),
                                  'markdown_blocks': list(range(j1, j2)),
                                  'published': P[i1:i2], 'markdown': M[j1:j2]})

    # Images, as rendered (a commented-out image is gone), in order.
    src = lambda h: [html.unescape(u) for u in re.findall(r'<img\b[^>]*\bsrc="([^"]+)"',
                                                           re.sub(r'<!--.*?-->', ' ', h, flags=re.S), re.I)]
    pub_imgs, imgs = src(pub_body), src(md_body)
    missing_imgs = [p for p in imgs if not re.match(r'https?://', p)
                    and not os.path.exists(os.path.join(root, p))]

    pub_items, pub_tables = shapes(pub_body)
    md_items, md_tables = shapes(md_body)
    pub_hidden, md_hidden = hidden(pub_body), hidden(md_body)

    # Link targets: every difference needs a "link" rule.
    link_rules = [(i, r) for i, r in enumerate(rules) if r.get('kind') == 'link']
    pl, ml = external_links(pub_body), external_links(md_body)
    link_diffs = []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, pl, ml, autojunk=False).get_opcodes():
        if op == 'equal':
            continue
        for k in range(max(i2 - i1, j2 - j1)):
            d = {'published': pl[i1 + k] if i1 + k < i2 else '', 'markdown': ml[j1 + k] if j1 + k < j2 else ''}
            hit = next((i for i, r in link_rules if r['published'] == d['published']
                        and r['markdown'] == d['markdown'] and uses.get(i, 0) < r.get('count', 1)), None)
            if hit is None:
                link_diffs.append(d)
            else:
                uses[hit] = uses.get(hit, 0) + 1

    empty = [side for side, toks in (('published', A), ('markdown', B)) if not toks]
    report = {
        'published_tokens': len(A), 'markdown_tokens': len(B), 'token_match_ratio': round(ratio, 5),
        'diff_regions': len(diffs), 'accepted_deviations': len(accepted),
        'headings_published': len(pub_heads), 'headings_missing': missing_heads,
        'internal_links': len(links), 'broken_internal_links': broken,
        'code_blocks_published': len(P), 'code_blocks_markdown': len(M),
        'code_blocks_differing': code_mismatch,
        'images_published': len(pub_imgs), 'images_markdown': len(imgs),
        'images_differing': [] if pub_imgs == imgs else [p for p in difflib.unified_diff(pub_imgs, imgs, lineterm='', n=0)
                                                         if p[:1] in '+-' and p[:3] not in ('---', '+++')],
        'images_missing_on_disk': missing_imgs,
        'external_links_published': len(pl), 'external_links_differing': link_diffs,
        'list_items_published': pub_items, 'list_items_markdown': md_items,
        'tables_published': pub_tables, 'tables_markdown': md_tables,
        'hidden_or_struck_published': pub_hidden, 'hidden_or_struck_markdown': md_hidden,
        'empty': empty, 'pandoc': pandoc,
        'allow_rules_unused': [r for i, r in enumerate(rules) if i not in uses],
        'diffs': diffs, 'accepted': accepted,
    }
    if a.json:
        with open(a.json, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=1, ensure_ascii=False)
    for k, v in report.items():
        if k not in ('diffs', 'accepted', 'allow_rules_unused', 'tables_published', 'tables_markdown'):
            print(f'{k}: {v if not isinstance(v, list) else (len(v), v)}')
    for d in diffs:
        print(f"\n[{d['op']}] ...{d['context_before']}\n  PUB: {d['published']}\n  MD : {d['markdown']}")
    for d in accepted:
        print(f"ACCEPTED: PUB[{d['published']}] MD[{d['markdown']}] -- {d['reason']}")
    for r in report['allow_rules_unused']:
        print(f"UNUSED ALLOW RULE: {r}")
    print(f"tables: {len(pub_tables)} published, {len(md_tables)} markdown, "
          f"{'identical' if pub_tables == md_tables else 'DIFFERENT (see --json)'}")
    ok = (not diffs and not missing_heads and not broken and not code_mismatch
          and not missing_imgs and imgs == pub_imgs and not empty and not link_diffs
          and pub_items == md_items and pub_tables == md_tables and pub_hidden == md_hidden
          and not report['allow_rules_unused'])
    print('\nRESULT:', 'PASS' if ok else 'FAIL')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
