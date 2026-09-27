#!/usr/bin/env python3
# Copyright 2026 OASIS Open
# SPDX-License-Identifier: Apache-2.0
# Authored by Michael Coletta, Technical Advisor to OASIS Open.
"""Put page numbers in the PDF's table of contents.

Chrome cannot number a table of contents as it prints (no CSS
target-counter), but the PDF it prints carries a named destination, with its
page, for every heading id. This reads those pages back (poppler's
pdfinfo -dests) and writes them into the HTML's table of contents, with dot
leaders, as a published OASIS PDF shows them. The caller prints again and
repeats until the pages stop moving: step 2 (pdf_renderer.PdfRenderer) with
wkhtmltopdf, and render/render.sh with Chrome. Standard library only, so it
also runs as a script.

Usage: toc_pages.py IN.html PRINTED.pdf OUT.html
Prints the number of entries numbered and how many changed since IN.html.
Exit 2 when the HTML has no table of contents or an entry has no page.
"""
import html
import re
import subprocess
import sys

CSS = """<style id="toc-pages">
/* Floats and a positioned rule, not flexbox: wkhtmltopdf's QtWebKit ignores
   flexbox, and the same markup has to print in it and in Chrome. An inline
   block keeps an <ol>'s own numbers beside its first line. The number
   floats right; the dot leader runs under the whole line and the title and
   number, on the page's white, cover it where they sit. */
.toc-line { display: inline-block; width: 100%; vertical-align: top; position: relative; overflow: hidden; }
.toc-page { float: right; padding-left: 0.35em; background: #fff; position: relative; z-index: 1; }
.toc-text { background: #fff; padding-right: 0.35em; position: relative; z-index: 1; }
.toc-dots { position: absolute; left: 0; right: 0; bottom: 0.3em; border-bottom: 1px dotted #666; z-index: 0; }
</style>"""


def dests(pdf):
    out = subprocess.run(['pdfinfo', '-dests', pdf], capture_output=True, text=True, check=True).stdout
    return {m.group(2): int(m.group(1)) for m in re.finditer(r'^\s*(\d+)\s+\[[^\]]*\]\s+"([^"]*)"', out, re.M)}


def text_pages(pdf, entries):
    """{target: page} found by text: each entry's title, searched from the
    page after the contents and never before the previous entry's page.
    wkhtmltopdf writes its internal links as explicit page destinations, not
    named ones, so pdfinfo -dests has nothing to read there."""
    text = subprocess.run(['pdftotext', '-layout', pdf, '-'], capture_output=True, text=True,
                          check=True).stdout.split('\f')
    flat = [re.sub(r'\s+', ' ', t).lower() for t in text]
    start = next((i for i, t in enumerate(flat) if 'table of contents' in t), -1) + 1
    while start < len(flat) and 'table of contents' in flat[start]:
        start += 1
    # the contents may run over several pages: skip those that list the first title
    if entries:
        first = entries[0][1]
        while start < len(flat) and first in flat[start] and flat[start].count(first) and \
                sum(1 for _, t in entries[:10] if t in flat[start]) > 3:
            start += 1
    found, at = {}, start
    for target, title in entries:
        k = next((i for i in range(at, len(flat)) if title in flat[i]), None)
        if k is not None:
            found[target] = k + 1
            at = k
    return found


ENTRY = re.compile(r'(?P<pre>(?:<li\b[^>]*>|<br\s*/?>)?\s*)(?P<num>[^<>]*?)'
                   r'(?P<a><a href="#(?P<t>[^"]+)">(?P<label>.*?)</a>)', re.S)


def main(src, pdf, out):
    """Number the contents of src (the unnumbered HTML, never changed) from
    pdf's pages into out, and return how many numbers differ from the ones
    out held before. A contents entry is a list item or a line: optional
    text (a section number), then a link to the heading. Pages come from
    the PDF's named destinations, else from where the entry's text is
    printed (text_pages)."""
    h = open(src, encoding='utf-8').read()
    m = re.search(r'<h([1-6])[^>]*id="table-of-contents"[^>]*>.*?</h\1>\s*(?=<(ul|ol)\b)', h, re.S)
    if not m:
        raise LookupError('toc_pages.py: no table of contents (a heading with id table-of-contents followed by a list)')
    tag, start, depth, end = m.group(2), m.end(), 0, None
    for t in re.finditer(rf'<(/?){tag}\b[^>]*>', h[start:]):
        depth += -1 if t.group(1) else 1
        if depth == 0:
            end = start + t.end()
            break
    toc = h[start:end]
    entries = [(e.group('t'), re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', '', e.group('num') + e.group('label')))).strip().lower())
               for e in ENTRY.finditer(toc)]
    pages = dests(pdf)
    if any(t not in pages for t, _ in entries):
        pages = {**text_pages(pdf, [(t, l) for t, l in entries if t not in pages]), **pages}
    try:
        old = dict(re.findall(r'<span class="toc-page" data-for="([^"]+)">(\d+)</span>',
                              open(out, encoding='utf-8').read()))
    except OSError:
        old = {}
    missing, changed, n = [], 0, 0

    def number(e):
        nonlocal changed, n
        target = e.group('t')
        if target not in pages:
            missing.append(target)
            return e.group(0)
        n += 1
        changed += old.get(target) != str(pages[target])
        return (f'{e.group("pre")}<span class="toc-line"><span class="toc-page" data-for="{target}">{pages[target]}</span>'
                f'<span class="toc-text">{e.group("num")}{e.group("a")}</span><span class="toc-dots"></span></span>')
    toc = ENTRY.sub(number, toc)
    # a numbered line is a block of its own: the line break after it goes
    toc = re.sub(r'(<span class="toc-dots"></span></span>)\s*<br\s*/?>', r'\1', toc)
    if missing:
        raise LookupError(f'toc_pages.py: no page in {pdf} for {missing}')
    h = h[:start] + toc + h[end:]
    h = h.replace('</head>', CSS + '</head>', 1)
    open(out, 'w', encoding='utf-8').write(h)
    print(f'numbered {n} contents entries, {changed} changed')
    return changed


if __name__ == '__main__':
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    try:
        main(*sys.argv[1:])
    except LookupError as e:
        sys.exit(str(e))
