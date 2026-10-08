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
locally with no GitHub Actions involved. The repository has six other
workflows:

| Workflow file | Role |
|---|---|
| `ci.yml` | Runs the test suite on every push and pull request. |
| `pub-check.yml` | Runs the OASIS publication checks on one stage directory, started by hand. |
| `make-manifest.yml` | Writes the release manifests for a stage directory, started by hand. |
| `convert-and-verify.yml` | The reusable workflow a TC repository calls to convert, render, verify and check one Markdown specification ([guide](docs/CONVERT-AND-VERIFY.md)). |
| `gate-change-review.yml` | Requires a pull request that changes the checker to record an adversarial review. |
| `move-v1.yml` | Moves the floating `v1` tag to each v1.x.y release when it is published. |

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

One command runs the whole stage:

```bash
python3 .github/src/step_1_markdown_to_html_converter_V3_0.py \
  path/to/spec.md "$(pwd)" path/to/dir --md-format --md-to-html
```

It needs `prettier`, `pandoc`, and the Python packages `beautifulsoup4` and
`requests`. The HTML is written next to the Markdown, with the same name. The
step 1 workflow runs the same script twice, first with `--md-format` and then
with `--md-to-html`. Either flag can be given on its own.

`--md-format` formats the Markdown in place:

```bash
prettier --write spec.md
```

`--md-to-html` then runs pandoc (the invocation in
`.github/src/pipeline/html_converter.py`) and the Python post-processor
described below:

```bash
pandoc spec.md \
  -f markdown+autolink_bare_uris-implicit_figures \
  --preserve-tabs \
  --no-highlight \
  -c https://docs.oasis-open.org/styles/markdown-styles-v1.7.3.css \
  -s \
  -o .pandoc-tmp-<pid>.html \
  --metadata title="<document title>"
```

The title is the Markdown's first level-one heading. pandoc writes to a
scratch file named for the process (`.pandoc-tmp-<pid>.html`) in the output
directory, so two conversions running at once cannot overwrite each other's
output. The scratch file is removed afterwards. If a `styles/styles.css` sits
beside the output, `-c` points at that file and not at the published
stylesheet. prettier and pandoc each have a time limit of 1800 seconds.

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
knowledge lives. Its 13 transforms are listed in `HtmlConverter.TRANSFORMS`
and run in this order:

1. `strip-pandoc-header`: removes pandoc's title block
   (`<header id="title-block-header">`).
2. `inject-meta-description`: adds a `<meta name="description">`, taken from
   a `description:` line in the Markdown (front matter or an HTML comment).
3. `remove-base-href`: removes any `<base>` tag. A base href breaks
   fragment-only links (`#section`) in the table of contents.
4. `drop-logo-figures`: removes the `<figure>` wrapper pandoc puts around the
   OASIS logo, whose caption would print the alt text.
5. `drop-nav-blocks`: removes stray `<nav>` contents blocks. The document
   carries its own Table of Contents section.
6. `enforce-single-logo`: keeps exactly one OASIS logo, as the first element
   of the body, pointing at
   `https://docs.oasis-open.org/templates/OASISLogo-v3.0.png`.
7. `fix-top-banner`: normalises the logo and title banner. It removes stray
   `<hr>` elements, adds a styled one, and turns the first `<h1>` into
   `<h1big>`.
8. `remove-duplicate-heading-anchors`: removes an anchor inside a heading
   that repeats the heading's own id.
9. `normalize-same-doc-anchors`: rewrites a link to this same document as a
   fragment-only link, so the contents work both as a local file and under
   the published `docs.oasis-open.org` URL.
10. `linkify-plain-urls`: turns a bare `http` or `https` URL in a paragraph
    that has no other markup into an `<a>` link.
11. `localize-css`: downloads remote stylesheets into `styles/` beside the
    HTML and points the `<link>` tags at the copies. It runs only when `HTML_LOCALIZE_CSS` is
    `1`, `true` or `yes`.
12. `localize-images`: always runs. It downloads every remote image into
    `images/` and points `src` at the copy, dropping `srcset`. An image that
    cannot be fetched is removed from the HTML.
13. `relativize-same-scope-links`: rewrites absolute links, stylesheets,
    scripts and images under the document's own published directory as
    relative paths.

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
contents; the `pdf-toc-pages` check reports one that does not.

The preprocessor also removes any `<base href>` from the PDF copy, after
making relative hyperlinks absolute against it, so stylesheets and images
load from the package being rendered and not from the live site.

The injected CSS also caps every image at the line width
(`img { max-width: 100%; height: auto; }`), so a figure with no width of its
own prints inside the margins instead of at its natural size.

The injected CSS prints each code block as one block (since v1.13.0). The
OASIS Markdown stylesheet sets `pre { display: inline }`, which printed every
line of a code block in its own box: 447 of the 667 multi-line blocks in the
CSAF v2.1 CSD03 PDF. The preprocessor sets `pre { display: block }` and
removes the frame from the `<code>` inside a `<pre>` and from pandoc's
`div.sourceCode` wrapper. Inline `<code>` is unchanged.

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

Every external tool in Stage 2 has a time limit (since v1.13.0):
`wkhtmltopdf` 1800 seconds, and `pdfinfo` and `pdftotext` 300 seconds each.
Each tool runs in its own process group, which is stopped when the limit is
reached, and the error names the tool. A `wkhtmltopdf` that runs out of time
fails the render. A `pdfinfo` or `pdftotext` that runs out of time, or fails,
leaves the contents unnumbered, and the `pdf-toc-pages` check reports it.

Where TC PDFs are made matters here. The step 2 workflow in this repository
runs only when started by hand, and no TC repository calls it. TC PDFs built
through the Publication Console come from publisher-toolkit's step 2, which
copies this stage's code into `lib/pa_pipeline` (the release it copied is
recorded in `lib/pa_pipeline/VENDORED.json`). Both of its renderers, Chrome
and `wkhtmltopdf`, run this preprocessor and print on A4 with the footer
described above.

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
printed unnumbered, and the `pdf-toc-pages` check says so.

A note on renderers: wkhtmltopdf is what this repository's workflows run.
publisher-toolkit can also print with headless Chrome, using CSS Paged Media:
an injected `@page` block sets A4 and the footer, with no running header. wkhtmltopdf's limits, for anyone evaluating alternatives:
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
pages. For a DocBook specification, the [`docbook-markdown` action](docs/MARKDOWN-EDITION.md) runs this for you.

Every defect class these transforms guard against (the lint codes D1, D2, D3,
D6 and D7, and the post-render assertions A1 and A2) can be checked in a TC's
own build before submission, with [oasis-pub-check](pub-check/):
`python3 pub-check/oasis_pub_check.py <stage-dir>`.

---

**The documentation set:** [Repository overview](README.md) · [TC guide](PUBLICATION-QUALITY.md) · [The acceptance criteria tool](pub-check/README.md) · [The criteria catalog](pub-check/CHECKS.md) · [Worked example](examples/eox-core-v1.0-csd01/README.md) · [Architecture diagrams](assets/architecture/README.md)
