<!--
Copyright 2026 OASIS Open
SPDX-License-Identifier: Apache-2.0
Authored by Michael Coletta, Technical Advisor to OASIS Open.
-->

# render: a Markdown specification rendered, staged and checked

`render.sh` turns one OASIS Markdown specification into the package OASIS
would publish, laid out at its `docs.oasis-open.org` path, and runs the
publication checks on it. A TC can see the verdict TC Administration will see while the document
is still the TC's to change. The walkthrough is
[docs/CONVERTING.md](../docs/CONVERTING.md).

| File | Role |
|---|---|
| `render.sh` | Stage, render (HTML, then PDF), number the contents, check |
| `footer.py` | Read from the document: the stage path, and the PDF footer (name, track, copyright line, date) |
| `print_pdf.mjs` | HTML to PDF in headless Chrome on the pipeline's A4 geometry, with that footer |
| `compare.mjs` | The published and rendered HTML side by side at named anchors |
| `review_pairs.py` | Published and rendered PDF pages paired for a reviewer, with a planted fault; then the review graded |

Requirements:
- pandoc 3.x;
- Python 3.10 or later with `beautifulsoup4`;
- poppler (`pdfinfo`, `pdftotext`);
- Node.js 18 or later (`render.sh` installs `puppeteer-core` next to itself on
  first run);
- Chrome or Chromium (set `CHROME` if it is not found).

```bash
render/render.sh MD_DIR SCHEMAS_DIR OUT_ROOT     # SCHEMAS_DIR "-" when there are none
```

- **Stage.** The stage path is read from the document's "This stage" URL. The
  `.md`, everything beside it and the schemas are copied to
  `OUT_ROOT/<path>/`.
- **HTML.** The pipeline's step 1 (`.github/src/step_1_markdown_to_html_converter_V3_0.py`)
  makes the HTML.
- **PDF.** Step 2's print styles (`fix_html_for_pdf.py`: type scale, code
  wrapping, figure caps) are applied, then Chrome prints. The footer is the
  one published OASIS PDFs carry: the document name and "Standards Track Work
  Product" (or "Non-Standards Track" for a Committee or Project Note) on the
  left, the copyright line in the centre, the document's date and "Page x of
  y" on the right. Nothing in the footer comes from the day of the render.
- **Contents.** Chrome cannot number a table of contents as it prints.
  `.github/src/pipeline/toc_pages.py` (shared with step 2) reads each heading's page from the PDF and writes it in, and
  the PDF is printed again until no number moves.
- **Check.** The script runs `pub-check/oasis_pub_check.py` on the staged
  package, and its exit status is the checks': 0 publishable, 1 blockers.
  With `PUBCHECK=0` it stops after staging; CI then runs the checks through the
  action.

`render.sh` prints with Chrome, which GitHub's runners and most desktops
already have. The pipeline's own PDF step prints with wkhtmltopdf. Both
print the same published footer and numbered contents; until proposal 012
(v1.9.0) the wkhtmltopdf step printed the file name with `.html`, the day of
the render, no track line, and a running title header.

## compare.mjs

```bash
CHROME=/path/to/chrome node render/compare.mjs PUBLISHED RENDERED OUT_DIR cover,toc,core_entry
```

For each anchor, both pages are scrolled to the element and the viewport is
captured as `<n>-<anchor>-published.png` and `<n>-<anchor>-rendered.png`.
`cover` is the top of the page, and `toc` finds either contents list. An
anchor missing on either side exits 1: the editions differ in structure
there. The pictures are for a person to read. The verifier
([`verify/`](../verify/README.md)) is the check on the words.

## review_pairs.py

```bash
python3 render/review_pairs.py make RENDERED.pdf PUBLISHED.pdf OUT_DIR --key KEY.json [--sample 30] [--seed N] [--plant KIND]
python3 render/review_pairs.py grade KEY.json REVIEW.json [RERUN.json...]
```

Requires poppler and Pillow. `make` pairs each rendered page it samples
(every page with a figure or image, the cover, the contents, and `--sample`
random pages) with the published page sharing most of its words, aligned in
document order, and writes each pair as one image (published left) with the
reviewer's brief, `PROMPT.md`. One more pair is a planted fault: a real page
with its footer, a band of text, or (on a contents page) its page numbers
erased on the right. `KEY.json` records which; keep it where the reviewer
cannot read it (`make` refuses a key inside `OUT_DIR`).

The brief asks for lines copied from both sides before any judgement, and
every kind of element on each side. `grade` counts as evidence only a
distinct line of eight or more letters and digits that is not on most pages
(a bracket, "1" or a footer proves nothing), needs three of those per side
(fewer on a page with fewer), and rejects a pair whose lines are not on its
page. It accepts the review only when the planted fault is named for what it
is ("page numbers", "footer", "missing"), and not by a word the reviewer
writes about most pairs.
It prints every other difference for a person to rule on. Pass a re-run of
the rejected pairs after the first review: later answers replace earlier.

Why so strict: on the DMLex pairs a Haiku reviewer copied lines that are not on
the page for 21 of 36 pairs, and its "difference" on the planted pair described text that is
not on the page. A grader that counted any difference as a catch passed it.

## Tests

`tests/test_render.py` renders the DMLex v1.0 OS Markdown edition and checks
four things:
- the footer on page 3 against the document;
- every contents number against the page its heading is printed on;
- pub-check's verdict on the PDF;
- `compare.mjs` against the published page.
