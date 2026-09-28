<!--
Copyright (c) OASIS Open 2026. All Rights Reserved.

This document may be copied, published, and distributed to others without
restriction, provided it is reproduced verbatim and this notice is retained.
Derivative works of this document are not permitted without prior written
authorization from OASIS Open, other than translation into languages other
than English. This document is the canonical statement of the publication
acceptance criteria it describes; the accompanying software is separately
licensed under the Apache License 2.0 (see LICENSE at the repository root).
Author: Michael Coletta, Technical Advisor to OASIS Open.
-->

# Pipeline transforms, run locally

**Author: Michael Coletta, Technical Advisor, OASIS Open**

The three document-transform workflows in this repository (`step_1`, `step_2`,
`step_3`) are thin CI wrappers. Each one wraps a small number of plain
commands. This page lists those commands so the transforms can be read and run
locally with no GitHub Actions involved. The other three workflows (`ci`,
`pub-check`, `make-manifest`) run the test suite, the publication checks and
the manifest emitter, and are documented in the README.

The rest of each transform workflow is CI plumbing and does not change the
document:
repository checkout, venv creation, `chmod`, input validation, git commit and
push, and `touch`-based timestamp management.

## Map

| Workflow file | What it actually runs | Output |
|---|---|---|
| `step_1_format_md_and_convert_to_html.yml` | `prettier`, then `pandoc`, then one Python post-processor | `spec.html` |
| `step_2_convert_md_to_html_pdf_final.yml` | one Python HTML preprocessor, then `wkhtmltopdf` | `spec.pdf` |
| `step_3_create_zipfile.yml` | `zip` | `spec.zip` |

Before these, a specification published in DocBook can be converted to
Markdown and checked word for word against its publication
(`converters/docbook-to-markdown/build.sh`, `verify/verify_md.py`), and after
them `render/render.sh` runs Stage 1 and Stage 2's preprocessor for one
document, prints the PDF in Chrome and checks it. See
[Conversion and local rendering](#conversion-and-local-rendering).

## Stage 1: Markdown to HTML

Three commands, in order:

```bash
# 1. Normalize the markdown in place
prettier --write spec.md

# 2. Base conversion (the invocation in .github/src/pipeline/html_converter.py)
pandoc spec.md \
  -f markdown+autolink_bare_uris-implicit_figures \
  --preserve-tabs \
  --no-highlight \
  -c https://docs.oasis-open.org/styles/markdown-styles-v1.7.3.css \
  -s \
  --metadata title="<document title>" \
  -o temp_output.html

# 3. OASIS-specific HTML fix-ups (see list below)
python3 .github/src/step_1_markdown_to_html_converter_V3_0.py \
  path/to/spec.md "$(pwd)" path/to/dir --md-format --md-to-html
```

`--preserve-tabs` keeps a tab in a code block a tab: without it pandoc expands
tabs to spaces, and 9 of the 316 code blocks in DMLex no longer matched the
published standard.

`-implicit_figures` stops pandoc wrapping a bare image line in
`<figure>`/`<figcaption>`, where the alt text renders as a visible caption.
Leaving out `+hard_line_breaks` keeps standard markdown semantics, a soft
newline being a space rather than a `<br/>`. `--no-highlight` keeps fenced
code blocks as plain `<pre><code>`, so the stylesheet's block background is
not broken into per-token bars. There is no `--toc` because the OASIS template
carries a hand-authored Table of Contents at its own position in the source.

The Python post-processor (`HtmlConverter._post_process_html` in
`.github/src/pipeline/html_converter.py`, reached through the
`step_1_markdown_to_html_converter_V3_0.py` shim) is where the OASIS-specific
knowledge lives. It applies, in order:

1. Drops the pandoc-generated `<header>` block and stray `<nav>` TOC
   (the document carries its own Table of Contents section).
2. Injects a `<meta name="description">` derived from the abstract.
3. Removes any `<base href>` tag. A base href silently breaks
   fragment-only links (`#section`) in the TOC.
4. Enforces exactly one OASIS logo image, pointing at the canonical
   `https://docs.oasis-open.org/templates/OASISLogo-v3.0.png`.
5. Normalizes the top banner block (logo / title / stage lines).
6. Removes duplicate heading anchor IDs (pandoc emits duplicates for
   repeated heading text; only the first survives).
7. Rewrites same-document anchors so they work both as a local file and
   under the published `docs.oasis-open.org` URL.
8. Converts remaining plain-text URLs to `<a>` links.
9. Optionally localizes remote CSS and images next to the HTML
   (`HTML_LOCALIZE_CSS=1`).

## Stage 2: HTML to PDF

Two commands:

```bash
# 1. Inject targeted monospace/code-block CSS without touching the OASIS styles
python3 .github/src/fix_html_for_pdf.py spec.html -o .spec-pdf.html

# 2. Render (the argument vector PdfRenderer.build_command returns)
wkhtmltopdf \
  --page-size A4 --orientation Portrait \
  --margin-top 25mm --margin-right 20mm --margin-bottom 25mm --margin-left 20mm \
  --footer-html .spec-footer.html --footer-spacing 4 \
  --no-outline --print-media-type \
  --disable-smart-shrinking --dpi 288 \
  --enable-local-file-access \
  --load-error-handling ignore \
  --load-media-error-handling ignore \
  .spec-pdf.html spec.pdf
```

`.spec-footer.html` is the footer of a published OASIS PDF, which
`PdfRenderer.footer_html` builds from the document and removes after the
render: the document name on the left; the copyright line with "Standards
Track Work Product" (or "Non-Standards Track" for a Committee or Project Note)
beneath it in the centre; the document's own date and "Page x of y" on the
right. There is no running header. Until proposal 012 the footer printed the
file name with `.html`, wkhtmltopdf's `[date]` (the day of the render) and a
running title header on every page.

When the document has a table of contents (`id="table-of-contents"`),
`PdfRenderer` then numbers it: `.github/src/pipeline/toc_pages.py` reads each
heading's page from the printed PDF's named destinations (`pdfinfo -dests`),
writes the page numbers with dot leaders into a copy of the HTML, and the PDF
is printed again until no number moves. A published OASIS PDF numbers its
contents; the checks' `pdf-toc-pages` check reports one that does not.

The preprocessor also removes any `<base href>` from the PDF copy, after
making relative hyperlinks absolute against it, so stylesheets and images
load from the package being rendered and not from the live site.

The injected CSS also caps every image at the line width
(`img { max-width: 100%; height: auto; }`), so a figure with no width of its
own prints inside the margins instead of at its natural size.

The injected CSS also sets the print type scale in points: body 10pt, code
blocks and inline code 9pt, tables 9pt (code in tables 8.5pt), h1 16pt, h2
14pt, h3 12pt, h4 11pt, h5 and h6 10pt, matching the OASIS DocBook and Word
publications. `--disable-smart-shrinking --dpi 288` makes wkhtmltopdf print
those points at their size; without them it scales each document by its own
content width, and rounds fonts to whole pixels at 96 dpi. Headless Chrome
prints the same sizes with no flags. The footer is 8pt.

`.github/scripts/step_2_convert_html_to_pdf_V2_0.sh`, which the step 2
workflow runs, performs both commands: `fix_html_for_pdf.py` writes a hidden
copy (`.spec-pdf-<pid>-<n>.html`) beside the source, so relative CSS and images
resolve, and `step_2_convert_html_to_pdf.py --footer-name spec.html` renders
it, so the footer names the published file. The PDF is moved into place only
when the render succeeds, and the copy is removed afterwards. A stage directory
with more than one top-level HTML file is refused. A TC render
script such as the DMLex `tools/publication-assurance/render.sh` runs command 1
and then prints with headless Chrome.

Where TC PDFs are made matters here. The step 2 workflow in this repository
runs only when started by hand, and no TC repository calls it. TC PDFs built
through the Publication Console come from publisher-toolkit's own step 2,
which renders on Letter paper and does not run this preprocessor, so the
code-wrap and image-cap rules do not reach those PDFs yet.

Everything in the footer is read from the document being rendered, never from
the day of the render:
- the name is the published file's name without `.html`;
- the track is Non-Standards for a Committee or Project Note (cn, cnd, cnprd,
  pn, pnd, in any part or errata name);
- the copyright year or range comes from the document's own notice, decoded
  with its declared charset;
- the date is the cover's date line.

The contents' page numbers come from the printed PDF's named destinations or,
since wkhtmltopdf writes none, from the page each heading is printed on:
- a line equal to the entry's title, or to it after a section number;
- found in order, after the contents pages.

If the numbers cannot be read or do not settle in four passes, the PDF is
printed unnumbered, and the checks' `pdf-toc-pages` check says so.

A note on renderers: wkhtmltopdf is what this repository's workflows run, but
the production pipeline has since moved to headless Chrome print-to-PDF with
CSS Paged Media (an injected `@page` block supplies the running header and
footer natively) because plain pandoc-plus-wkhtmltopdf output was not adequate
for the requirement. wkhtmltopdf's limits, for anyone evaluating alternatives:
untagged PDF, no bookmarks/outline, no PDF/A conformance, and internal links
that depend on the anchor fix-ups from Stage 1. A toolchain that produces a
tagged PDF with a real outline (for example typst) improves on each of those
points.

## Stage 3: Package

```bash
cd path/to/stage-dir && zip -r ../spec-version-stage.zip .
```

The workflow additionally runs `touch -d "<date> 17:00:00 UTC"` across the
directory, which sets every published file's timestamp to the publication
date.

## Conversion and local rendering

```bash
# DocBook to OASIS Markdown, with the specification's profile, verified against the publication
converters/docbook-to-markdown/build.sh --profile dmlex SPEC_DIR OUT_DIR PUBLISHED_URL
# any Markdown edition against its published HTML, word for word
python3 verify/verify_md.py SPEC.md PUBLISHED_URL --allow ALLOW.json --json report.json
# render, stage at the docs.oasis-open.org path, check
render/render.sh MD_DIR SCHEMAS_DIR OUT_ROOT
```

`render.sh` uses Stage 1 as above and Stage 2's preprocessor, then prints in
headless Chrome rather than wkhtmltopdf. The footer is the one published
OASIS PDFs carry, read from the document (name, track, copyright line,
document date, page), and the table of contents is numbered from the printed
pages. The walkthrough is [docs/CONVERTING.md](docs/CONVERTING.md).

Every defect class these transforms guard against (the lint series D1-D7 and
the post-render assertions A1/A2) is enforceable in a TC's own build before
submission, via [oasis-pub-check](pub-check/):
`python3 pub-check/oasis_pub_check.py <stage-dir>`.

---

**The documentation set:** [Repository overview](README.md) · [TC guide](PUBLICATION-QUALITY.md) · [The acceptance criteria tool](pub-check/README.md) · [The criteria catalog](pub-check/CHECKS.md) · [Worked example](examples/eox-core-v1.0-csd01/README.md) · [Architecture diagrams](assets/architecture/README.md)
