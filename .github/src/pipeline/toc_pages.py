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


def _lines(page):
    return [re.sub(r'\s+', ' ', l).strip().lower() for l in page.splitlines() if l.strip()]


def text_pages(pdf, entries):
    """{target: page} found by where each entry's heading is printed, for a
    PDF with no named destinations (wkhtmltopdf writes its internal links as
    explicit page destinations). A heading is a line of its own, so a line
    equal to the entry's title (or two lines that join into it) is looked
    for, not the title anywhere in the text: a cross-reference mentions a
    heading mid-sentence. The contents pages are skipped (their lines are the
    titles), and entries are found in order, so a repeated title ("Overview")
    is taken after the one before it."""
    text = subprocess.run(['pdftotext', '-layout', pdf, '-'], capture_output=True, text=True,
                          check=True).stdout.split('\f')
    pages = [_lines(t) for t in text]
    titles = [t for _, t in entries]
    title_set = set(titles)

    def contents_like(lines):
        hits = sum(1 for l in lines if any(l == t or l.startswith(t + ' ') for t in title_set))
        return hits >= 3 and hits >= 0.3 * len(lines)
    first = next((i for i, ls in enumerate(pages)
                  if any(l in ('table of contents', 'contents') for l in ls) and contents_like(ls)), None)
    at = 0
    if first is not None:
        at = first
        while at < len(pages) and contents_like(pages[at]):
            at += 1
    found = {}
    for target, title in entries:
        # the heading line: the title itself; the title after a section
        # number the contents list leaves to its <ol> ("1. Introduction");
        # else, last, the first mention after the previous entry's page
        numbered = re.compile(r'(?:\d+(?:\.\d+)*\.?|appendix [a-z]\.?)\s+' + re.escape(title))
        # "a references" in the contents, "Appendix A. References" on the page
        sec = re.match(r'([a-z](?:\.\d+)*|\d+(?:\.\d+)*)\.?\s+(.+)', title)
        lettered = (re.compile(r'(?:appendix |annex )?' + re.escape(sec.group(1)) + r'\.?\s+' + re.escape(sec.group(2)))
                    if sec else None)
        tests = (lambda ls: title in ls or any(a + ' ' + b == title for a, b in zip(ls, ls[1:])),
                 lambda ls: any(numbered.fullmatch(l) for l in ls),
                 lambda ls: bool(lettered) and any(lettered.fullmatch(l) for l in ls),
                 lambda ls: any(title in l for l in ls),
                 lambda ls: title in ' '.join(ls))  # a heading wrapped over several lines
        k = next((i for test in tests for i in range(at, len(pages)) if test(pages[i])), None)
        if k is not None:
            found[target] = k + 1
            at = k
    return found


def contents_span(h):
    """(start, end) of the contents list: the list right after the heading
    whose id is table-of-contents. Between them only comments, empty elements
    (<tocHere/>) and wrappers (<nav>, <div class="toc">, a <details>'
    </summary>) may stand; the heading is matched to its own closing tag and
    no further, so a later list of links is never taken for the contents."""
    m = re.search(r'<h([1-6])\b[^>]*id="table-of-contents"[^>]*>(?:(?!</?h[1-6]\b).)*?</h\1>'
                  r'(?:\s|<!--.*?-->|<[A-Za-z][\w-]*\b[^>]*/>|<([A-Za-z][\w-]*)\b[^>]*>\s*</\2>'
                  r'|<(?:nav|div|section)\b[^>]*>|</summary>)*'
                  r'(?=<(ul|ol)\b)', h, re.S)
    if not m:
        raise LookupError('toc_pages.py: no table of contents (a heading with id table-of-contents followed by a list)')
    tag, start, depth = m.group(3), m.end(), 0
    for t in re.finditer(rf'<(/?){tag}\b[^>]*>', h[start:]):
        depth += -1 if t.group(1) else 1
        if depth == 0:
            return start, start + t.end()
    raise LookupError('toc_pages.py: the contents list is never closed')


ENTRY = re.compile(r'(?P<pre>(?:<li\b[^>]*>|<br\s*/?>)?\s*)'
                   r'(?P<num>(?:[^<>]|<(?!/?(?:li|a|ul|ol|br)\b)[^>]*>)*?)'
                   r'(?P<a><a\b[^>]*?\bhref="#(?P<t>[^"]+)"[^>]*>(?P<label>.*?)</a>)', re.S)


def entry_title(e):
    """An entry's title as printed: its section number and link text."""
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', '', e.group('num') + e.group('label')))).strip().lower()


def main(src, pdf, out):
    """Number the contents of src (the unnumbered HTML, never changed) from
    pdf's pages into out, and return how many numbers differ from the ones
    out held before. A contents entry is a list item or a line: optional
    text (a section number), then a link to the heading. Pages come from
    the PDF's named destinations, else from where the entry's heading is
    printed (text_pages)."""
    h = open(src, encoding='utf-8').read()
    start, end = contents_span(h)
    toc = h[start:end]
    entries = [(e.group('t'), entry_title(e)) for e in ENTRY.finditer(toc)]
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
    if not n:
        raise LookupError(f'toc_pages.py: no page in {pdf} for any contents entry')
    if missing:
        # left unnumbered rather than guessed; the gate's pdf-toc-pages check
        # grades the contents as printed
        print(f'toc_pages.py: no page found for {len(missing)} entries, left unnumbered: {missing}',
              file=sys.stderr)
    # a numbered line is a block of its own: the line break after it goes
    toc = re.sub(r'(<span class="toc-dots"></span></span>)\s*<br\s*/?>', r'\1', toc)
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
