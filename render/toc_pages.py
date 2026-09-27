#!/usr/bin/env python3
# Copyright 2026 OASIS Open
# SPDX-License-Identifier: Apache-2.0
# Authored by Michael Coletta, Technical Advisor to OASIS Open.
"""Put page numbers in the PDF's table of contents.

Chrome cannot number a table of contents as it prints (no CSS
target-counter), but the PDF it prints carries a named destination, with its
page, for every heading id. This reads those pages back (poppler's
pdfinfo -dests) and writes them into the HTML's table of contents, with dot
leaders, as a published OASIS PDF shows them. render.sh prints again and
repeats until the pages stop moving.

Usage: toc_pages.py IN.html PRINTED.pdf OUT.html
Prints the number of entries numbered and how many changed since IN.html.
Exit 2 when the HTML has no table of contents or an entry has no page.
"""
import re
import subprocess
import sys

CSS = """<style id="toc-pages">
.toc-line { display: flex; align-items: baseline; }
.toc-line > a { flex: 0 1 auto; }
.toc-dots { flex: 1 1 auto; border-bottom: 1px dotted #666; margin: 0 0.3em; min-width: 1em; }
.toc-page { flex: 0 0 auto; }
</style>"""


def dests(pdf):
    out = subprocess.run(['pdfinfo', '-dests', pdf], capture_output=True, text=True, check=True).stdout
    return {m.group(2): int(m.group(1)) for m in re.finditer(r'^\s*(\d+)\s+\[[^\]]*\]\s+"([^"]*)"', out, re.M)}


def main(src, pdf, out):
    h = open(src, encoding='utf-8').read()
    m = re.search(r'<h([1-6])[^>]*id="table-of-contents"[^>]*>.*?</h\1>\s*<ul>', h, re.S)
    if not m:
        sys.exit('toc_pages.py: no table of contents (a heading with id table-of-contents followed by a list)')
    depth, end = 0, None
    for t in re.finditer(r'<(/?)ul\b[^>]*>', h[m.end() - 4:]):
        depth += -1 if t.group(1) else 1
        if depth == 0:
            end = m.end() - 4 + t.end()
            break
    toc = h[m.end() - 4:end]
    pages = dests(pdf)
    old = dict(re.findall(r'<span class="toc-page" data-for="([^"]+)">(\d+)</span>', toc))
    toc = re.sub(r'<span class="toc-line">(<a href="#[^"]+">.*?</a>)<span class="toc-dots"></span>'
                 r'<span class="toc-page"[^>]*>\d+</span></span>', r'\1', toc, flags=re.S)
    missing, changed, n = [], 0, 0

    def number(a):
        nonlocal changed, n
        target = a.group(1)
        if target not in pages:
            missing.append(target)
            return a.group(0)
        n += 1
        changed += old.get(target) != str(pages[target])
        return (f'<span class="toc-line">{a.group(0)}<span class="toc-dots"></span>'
                f'<span class="toc-page" data-for="{target}">{pages[target]}</span></span>')
    toc = re.sub(r'<a href="#([^"]+)">.*?</a>', number, toc, flags=re.S)
    if missing:
        sys.exit(f'toc_pages.py: no page in {pdf} for {missing}')
    h = h[:m.end() - 4] + toc + h[end:]
    if 'id="toc-pages"' not in h:
        h = h.replace('</head>', CSS + '</head>', 1)
    open(out, 'w', encoding='utf-8').write(h)
    print(f'numbered {n} contents entries, {changed} changed')
    return changed


if __name__ == '__main__':
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    main(*sys.argv[1:])
