<!--
Copyright 2026 OASIS Open
SPDX-License-Identifier: Apache-2.0
Authored by Michael Coletta, Technical Advisor to OASIS Open.
-->

# render: a Markdown specification rendered, staged and gated

`render.sh` turns one OASIS Markdown specification into the package OASIS
would publish, laid out at its `docs.oasis-open.org` path, and runs the gate
on it. A TC can see the verdict TC Administration will see while the document
is still the TC's to change. The walkthrough is
[docs/CONVERTING.md](../docs/CONVERTING.md).

| File | Role |
|---|---|
| `render.sh` | Stage, render (HTML, then PDF), number the contents, gate |
| `footer.py` | Read from the document: the stage path, and the PDF footer (name, track, copyright line, date) |
| `print_pdf.mjs` | HTML to PDF in headless Chrome on the pipeline's A4 geometry, with that footer |
| `compare.mjs` | The published and rendered pages side by side at named anchors |

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
- **Gate.** The script runs `pub-check/oasis_pub_check.py` on the staged
  package, and its exit status is the gate's: 0 publishable, 1 blockers.
  With `PUBCHECK=0` it stops after staging; CI then runs the gate through the
  action.

The pipeline's own step 2 (wkhtmltopdf) is not used for the PDF because its
footer does not match the published footer:
- it prints the file name with `.html`;
- it prints the date of the render;
- it has no track line;
- it puts the title as a running header on every page.

Proposal 012 fixes step 2 itself.

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

## Tests

`tests/test_render.py` renders the DMLex v1.0 OS Markdown edition and checks
four things:
- the footer on page 3 against the document;
- every contents number against the page its heading is printed on;
- the gate's verdict on the PDF;
- `compare.mjs` against the published page.
