<!--
Copyright 2026 OASIS Open
SPDX-License-Identifier: Apache-2.0
Authored by Michael Coletta, Technical Advisor to OASIS Open.
-->

# verify: an edition against what was published

`verify_md.py` checks the Markdown and its HTML against the published HTML;
`verify_pdf.py` checks the rendered PDF against the published PDF.

## verify_md: a Markdown edition against the published HTML

`verify_md.py` answers one question: does this Markdown file say exactly what
the published HTML of the same specification says? Use it when a TC converts
an existing specification (DocBook, Word) to the OASIS Markdown template and
has to show the conversion changed nothing.

Requirements: Python 3.10 or later (standard library only) and pandoc 3.x.
The Markdown is read with the reader the pipeline's step 1 publishes with
(`markdown+autolink_bare_uris-implicit_figures`), so what is verified is what
OASIS would publish; a lettered list (`a.`) is a list there, and plain text on
GitHub. Older pandoc releases parse Markdown differently and produce
differences that are not in the document; the tool refuses them and records
the version it used in the report.

Its companion `verify_pdf.py` compares the rendered PDF with the published
PDF ([below](#verify_pdf-the-rendered-pdf-against-the-published-pdf)).

```bash
python3 verify/verify_md.py SPEC.md PUBLISHED [--root DIR] [--allow FILE] (repeat --allow for more than one file) [--json OUT] [--rendered HTML]
```

| Argument | Meaning |
|---|---|
| `SPEC.md` | The Markdown edition |
| `PUBLISHED` | The published HTML: a saved file or an `https://docs.oasis-open.org/...` URL |
| `--root DIR` | Where the Markdown's image paths are resolved (default: the Markdown's directory) |
| `--allow FILE` | Accepted deviations, each with a reason (below); give it more than once to combine files |
| `--json OUT` | The full report, every difference in full |
| `--rendered HTML` | Verify this rendering of `SPEC.md`, the pipeline's step 1 output, instead of reading `SPEC.md` with pandoc. This is the HTML that is published, so it is the stronger check; add the profile's `allow-rendered.json` for what step 1 changes on purpose |

Exit `0` when every check passes, `1` when any fails, `2` when an input
cannot be read (a missing file, no pandoc, an allow rule without a reason).
The last line printed is `RESULT: PASS` or `RESULT: FAIL`.

## What it checks

| Check | Passes when |
|---|---|
| Words | Every published word appears in the Markdown in the same order, and nothing is added, apart from the allowed deviations. Both sides are reduced to visible text and aligned with `difflib`; tables of contents are left out of both. |
| Headings | Every numbered published heading is in the Markdown, in order |
| Code blocks | Same number of `<pre>` blocks, each identical in order (whitespace at line ends ignored) |
| Lists and tables | Same number of list items; every data table (two or more rows) has the same words in the same cells of the same rows |
| List numbering | Every ordered list numbered the same way, in order (`1`, `a`, `i`, `A`, `I`). List letters are not text, so a list numbered `1.`, `2.` where the publication has `a.`, `b.` keeps every word; DMLex's section 2 did, and its text refers to "point c. above" |
| Contents | The generated table of contents lists the same entries, in order. The contents are left out of the word comparison and compared here as a list; the first DMLex edition stopped at three levels and dropped the 38 A.2.2.x and F.1.2.x entries the publication lists |
| Images | The same image sources in the same order, as rendered (a commented-out image is gone), and every local one exists under `--root` |
| Link targets | The same external (http or https) link targets; the scheme is read as https |
| Hidden text | The same amount of struck-through (`~~`, `<del>`) or hidden (`display:none`) markup as the publication |
| Internal links | Every `#id` link in the Markdown has an anchor |
| Not empty | Neither side is empty |

`docs.oasis-open.org` is served through Cloudflare, which replaces each email
address with `[email protected]` and an encoded attribute. The verifier
decodes them, so a live URL and a saved copy give the same result.

## Reading the output

Each unexplained difference prints as

```
[replace] ...the words just before it
  PUB: the published words
  MD : the Markdown words
```

`replace` means the words changed, `delete` that the Markdown dropped them,
`insert` that it added them. Accepted deviations print as `ACCEPTED:` lines
with their reason. A rule that matched nothing prints as
`UNUSED ALLOW RULE:` and fails the run: it is stale, or it is half of a pair
(a paragraph that moved is a delete and an insert) whose other half was
deleted outright.

## The allow file

Some differences are intended: the OASIS Markdown template labels the stage
URLs "This stage" where an older DocBook edition said "This version", and the
HTML page footer is not document content. Each is written down once, with the
reason a reader can check:

```json
[
 {"published": "version", "markdown": "stage", "count": 3, "reason": "Naming Directives v1.7 labels"},
 {"published": ":", "markdown": "", "context": "Notices", "reason": "'Notices:' label rendered as a heading"},
 {"kind": "heading", "published": "F.1.2.1 csd04.xmlTracking of ...", "reason": "source defect"},
 {"kind": "link", "published": "https://www.oasis-open.org/", "markdown": "", "reason": "the logo link"}
]
```

`published` and `markdown` are the token strings the report prints, matched
exactly. A rule accepts one difference unless it gives `count`, and with
`context` only a difference whose preceding words end with that text. Any
difference no rule accepts fails the run, so the allow file is the complete,
reviewable list of every way the Markdown differs from the publication.

A rule's `kind` says what it accepts: `text` (the default) a difference in
the words, `heading` a published heading the Markdown words differently,
`link` a changed link target, and `image` a changed image source (with
`--rendered`, the pipeline serves the OASIS logo from the package's own
`images/` directory).

The DMLex rules are in
[`converters/docbook-to-markdown/profiles/dmlex/allow.json`](../converters/docbook-to-markdown/profiles/dmlex/allow.json).
With them, the DMLex v1.0 OASIS Standard Markdown edition matches
[the published HTML](https://docs.oasis-open.org/lexidma/dmlex/v1.0/os/dmlex-v1.0-os.html) on
61,260 tokens (words and punctuation marks), 311 headings, 316 code blocks, 1,133 list items, 93 external
links and 50 images
(`tests/test_verify_md.py`).

## What it does not check

Styling and page layout, which are the publication checks' job (`pub-check/`) and the
pipeline's; the rendered PDF, which `verify_pdf.py` compares. Nor structure
that keeps the words in order: a heading's level, a list item moved to
another nesting level, emphasis or a code span removed. Review those on the
pages (`render/review_pairs.py`), or read the diff of the Markdown itself.

## verify_pdf: the rendered PDF against the published PDF

```bash
python3 verify/verify_pdf.py RENDERED.pdf PUBLISHED.pdf|URL [--allow FILE]... [--json OUT]
```

An HTML contents list has no page numbers, so no HTML comparison can see a
PDF whose contents have none. The DMLex edition's first renders had none
against the published standard's 170, and passed every HTML check and a
side-by-side look at the contents page. `verify_pdf.py` reads both PDFs with
`pdftotext -layout` (poppler) and compares them the way `verify_md.py`
compares the HTML, every page:

| Check | Passes when |
|---|---|
| Words | Every published word is in the rendered PDF in the same order, apart from allowed deviations. List letters and numbers are text in a PDF, so a lettered list printed `1.`, `2.` is a difference |
| Contents | Each contents entry's page number is read as `<page>`: the two editions paginate differently, so the numbers need not match, but an entry numbered on one side and not the other is a difference |
| Running lines | The header and footer lines (a line near the page edge that repeats, digits aside, on two pages or more and half of them) are the same on both sides, and every rendered page carries one. Only the numbers that change from page to page and the page count after them are masked, so a footer with the wrong version, date or year is a difference |

What it takes as layout and counts rather than reports:
- line wrapping: the two sides are equal once spaces go and a hyphen that
  ends a line between two letters may vanish (FOP hyphenates, Chrome breaks
  a URL). Any other hyphen counts, so a lost minus sign is a difference;
- a moved block: three or more tokens deleted in one place and inserted,
  unchanged, within 400 tokens. A block that changed on the way is reported;
- list bullets, which a renderer may draw outside the text layer, and
  ligature glyphs, read as their letters.

Nothing else is waved through: two numbers that swap places, or a "NOT"
that moves from one sentence to another, is a difference.

The allow file is `verify_md.py`'s, with two more kinds.
`{"kind": "footer", "published": ..., "markdown": ..., "reason": ...}`
accepts a running line as the report prints it. `{"kind": "region", "from":
..., "to": ..., "reason": ...}` declares a stretch after the contents whose
order is not the document's to keep, a diagram regenerated from its source
for one. There the two sides must hold the same characters, in any order.
DMLex's is
[`profiles/dmlex/allow-pdf.json`](../converters/docbook-to-markdown/profiles/dmlex/allow-pdf.json).
It also records two defects of the published PDF itself: its font has no `ň`
or `ō`, and FOP printed `#` for them 15 times.

It does not see where a figure is drawn or what it looks like, nor type
size (pub-check's `pdf-legibility` and `pdf-type-scale` checks measure that).
The pictures need a reviewer: `render/review_pairs.py`.
