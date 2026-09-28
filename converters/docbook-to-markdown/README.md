<!--
Copyright 2026 OASIS Open
SPDX-License-Identifier: Apache-2.0
Authored by Michael Coletta, Technical Advisor to OASIS Open.
-->

# DocBook to OASIS Markdown

Converts an OASIS DocBook 4.5 specification into a single Markdown file in
the OASIS Markdown template (the layout of CSAF and NIEM: logo, title block,
front matter as level-4 headings, Notices, table of contents, numbered
sections with explicit anchors), then checks the result against the
published HTML with [`verify/verify_md.py`](../../verify/README.md). The
walkthrough for a TC is [docs/CONVERTING.md](../../docs/CONVERTING.md).

| File | Role |
|---|---|
| `build.sh` | Resolve XIncludes, run the profile's prebuild, convert, copy the images, verify |
| `docbook2md.py` | The converter: resolved DocBook XML to Markdown |
| `profiles/<spec>/profile.json` | What differs for one specification (below) |
| `profiles/<spec>/allow.json` | The accepted differences from its published HTML, each with a reason |
| `profiles/<spec>/allow-rendered.json` | The further differences the pipeline's own HTML makes on purpose, for `verify_md.py --rendered` |
| `profiles/<spec>/prebuild.sh` | Optional: figures the TC's own build generates |

Requirements: Python 3.10 or later (standard library only), `xmllint`
(libxml2), pandoc 3.x for verification, and whatever the profile's prebuild needs (DMLex: Graphviz `dot`
and `m4`). On Debian or Ubuntu: `apt-get install libxml2-utils graphviz m4`
plus the pandoc `.deb` from [github.com/jgm/pandoc/releases](https://github.com/jgm/pandoc/releases).

## Usage

```bash
converters/docbook-to-markdown/build.sh --profile dmlex SPEC_DIR OUT_DIR [PUBLISHED_HTML]
```

| Argument | Meaning |
|---|---|
| `--profile` | A profile name under `profiles/`, or a profile directory of your own |
| `SPEC_DIR` | The DocBook source directory (DMLex: `dmlex-v1.0/specification` in oasis-tcs/lexidma) |
| `OUT_DIR` | Receives `<basename>.md`, the images it references and, when verifying, `<basename>-verification.json` |
| `PUBLISHED_HTML` | Optional. The published HTML, a file or a URL. Omitted, verification is skipped |

The source tree is only read. XIncludes are resolved into a temporary
directory, and anything a prebuild generates is written there. The script
exits non-zero if the merge fails, if the converter meets a reference to an
unknown id or an element it does not handle, or if verification fails.

Regenerating the DMLex v1.0 OASIS Standard edition:

```bash
git clone https://github.com/oasis-tcs/lexidma.git
converters/docbook-to-markdown/build.sh --profile dmlex lexidma/dmlex-v1.0/specification out \
    https://docs.oasis-open.org/lexidma/dmlex/v1.0/os/dmlex-v1.0-os.html
```

`tests/test_docbook_to_markdown.py` runs exactly this against oasis-tcs/lexidma
at `e3c0626` and requires the Markdown edition committed in
MColetta-OASIS/lexidma, byte for byte.

## Profiles

`profile.json` holds what is specific to one specification. Everything else
is the shared OASIS DocBook stylesheet's behaviour and lives in the converter.

| Key | Meaning | Default |
|---|---|---|
| `spec` | The specification's name, for people reading the profile | none |
| `main` | The DocBook root file in `SPEC_DIR` | required |
| `dtd` | The local DocBook DTD, so nothing is fetched | required |
| `entities` | The entity file that declares `version`, `stage` and the rest | required |
| `basename` | The output name, filled from those entities | required |
| `merge_log_ignore` | One `xmllint` message to ignore (a known, harmless missing include) | none |
| `prebuild` | A script run as `prebuild.sh SPEC_DIR WORK_DIR EXTRA_DIR` | none |
| `glossterm_upper` | Uppercase `<glossterm>`, as the v1.43 stylesheet does for the BCP 14 key words | `false` |
| `figure_dpi` | Pixels per inch for a `<graphic contentwidth="...cm">` | `90` (DocBook XSL) |
| `code_languages` | The language label a code block gets, by the extension of the file it was included from (`xml:base`) | `.json`, `.xml`, `.sql` |
| `allow` | The allow file passed to the verifier | none |

The DMLex profile (`profiles/dmlex/`) is the first. A second specification
adds its own directory; the converter changes only when that specification
uses DocBook the converter does not yet handle.

## What the converter does

- `<glossterm>` is uppercased when the profile says so.
- A section or appendix with `role="normative"` or `role="informative"` gets
  ` (Normative)` or ` (Informative)` after its title.
- Every DocBook `id` becomes an HTML anchor, so `olink`, `xref` and `link`
  targets resolve and existing deep links into the published HTML still work.
- A cross-reference reads `Section N, "Title"` or `Appendix X, "Title"`, as
  DocBook generates it.
- Examples are numbered through the body (Example 1, 2, ...) and separately in
  each appendix (Example A.1, A.2, ...).
- Paragraphs placed directly in a section that holds a bibliography are
  omitted: the OASIS stylesheet suppresses them.
- An element whose `condition` attribute does not contain `oasis` is dropped,
  as the stylesheet drops it, after numbering: a hidden section still takes
  its number, so the sections after it keep the published numbers.
- Characters Markdown would read as markup are escaped: `* _ [ ] < > | $ ^`,
  an entity-like `&name;`, and a paragraph that starts like a numbered item
  (`2024.`) or a heading (`#`). Superscript and subscript become `<sup>` and
  `<sub>`. A cross-reference takes its target's number and title, its
  `xreflabel`, or its `endterm`.
- Program listings are fenced code blocks copied byte for byte.
- An ordered list is numbered as the DocBook stylesheet prints it: by its
  `numeration`, or else by how many ordered lists enclose it (`1.`, `a.`,
  `i.`, `A.`, `I.`, then round again). The pipeline's pandoc `markdown` reader
  prints `a.` as a lettered list; GitHub shows the letter as text. DMLex
  section 2 is lettered, and its text refers to "point c. above": before
  v1.10.0 the converter wrote `1.`, `2.`, `3.` there, and no comparison of the
  words could see it.
- The table of contents lists headings to three levels, counted in an
  appendix from its first section, as the stylesheet does: `A.2.2.1` is
  listed, `3.2.1.1` is not.
- A `<graphic>` with a `contentwidth` in centimetres becomes `<img width>` in
  pixels at `figure_dpi`. Without the width an SVG draws at its natural size
  and a large diagram runs off the page.

## What it refuses

The conversion stops (exit 1, the reason on stderr) rather than write
something that reads differently from the publication:

- an element it does not handle (`UNHANDLED block <...>`), rather than
  flattening it into paragraphs. Tables (`table`, `informaltable`) are the
  first a second specification is likely to meet; DMLex has none;
- content directly under `<article>` outside any section;
- a continued `<orderedlist>` (`continuation="continues"`), which Markdown
  cannot express, and a `numeration` it does not know;
- a cross-reference with no text to show (no title, `xreflabel` or `endterm`);
- a reference to an id that does not exist.

Add what is missing to the converter with a test; do not work around it in
the profile. A lone `~` is not escaped (DMLex's text has five, and escaping
them would change the edition); run the verifier on the rendered HTML
(`verify_md.py --rendered`) to catch any mark-up pandoc's `markdown` reader
finds in the text.

## Known DMLex source defects

These are in the DocBook source of the DMLex OASIS Standard. The converter
does not correct text; where a defect reaches the published HTML it reaches
the Markdown too, except the first, which is a markup error, not content.

1. `ReviewChangeTracking/csd04.xml` and `csd03.xml` each start their title
   with an empty `<ulink url="csd04.xml"/>` (or `csd03.xml`), so the published
   headings of F.1.2.1 and F.1.2.2 read `csd04.xmlTracking of changes ...`.
   The Markdown drops the empty link; the allow file records the difference.
2. In the same two files the link text of the CSD04 and CSD03 PDF links ends
   in `.pdf.pdf`.
3. The citation format in `dmlex.xml` reads `OASIS &standard;` and the entity
   already expands to `OASIS Standard`, so the citation reads "OASIS OASIS
   Standard".
4. The Makefile builds `dmlex_uml.svg` with GNU `head -n-1` and
   `#!/usr/bin/python`, neither on a stock macOS. The DMLex prebuild does the
   same with `python3`, `sed` and `tail`.
5. `nvh2dot.py` walks a Python set, so the diagram's cluster order and layout
   change from run to run. The prebuild fixes the hash seed, so a run is
   repeatable; the nodes and edges match the published `dmlex_uml.svg`.

## Traps for maintainers

- **Figure width.** A DocBook `<graphic contentwidth="16cm">` is sized by the
  stylesheet: 567 pixels at 90 dpi. Without an explicit width an SVG draws at
  its natural size, and the DMLex UML diagram ran off the page. The converter
  writes `<img width>` from the profile's `figure_dpi`.
- **Long inline code shrinks the PDF.** An unbreakable `code span` wider than
  the page makes a shrink-to-fit renderer print the whole document smaller.
  NIEM NDR v6.0 printed its 12pt body at 8pt. The pipeline's print styles wrap
  inline code, and the gate's `pdf-legibility` check measures the printed body
  size against the declared one.
- **Cloudflare hides email addresses.** `docs.oasis-open.org` replaces each
  address with `[email protected]` and an encoded attribute. The verifier
  decodes them. A tool that reads the page without decoding them sees seven
  missing addresses in DMLex's front matter.
- **The published page may not be UTF-8.** DMLex's is ISO-8859-1. The verifier
  takes the charset from the server, then the page, then the HTML default.
- **Generated figures change from run to run.** DMLex's `nvh2dot.py` walks a
  Python set, so its UML diagram's layout changes per run. The DMLex prebuild
  fixes the hash seed. Compare such figures by their contents, not their
  bytes.
- **pandoc versions differ.** The verifier reads the Markdown through pandoc's
  `markdown` reader, as the pipeline does, and requires 3.x; the DMLex result
  was made with 3.8.2.1.
- **List letters are not words.** DocBook numbers a list inside a list `a.`,
  and one inside that `i.`, unless told otherwise. A converter that writes
  `1.` keeps every word and changes what "point c. above" means. The
  converter numbers them as the stylesheet does; `verify_md.py` compares the
  numbering.
- **A wrapped contents entry.** Its page number belongs at the end of its
  last line. The pipeline's contents numbering puts it there (v1.10.0); it
  used to print on the first line, with the leader running to nothing.
- **The published PDF has defects of its own.** DMLex's prints `#` for two
  letters its font lacks. Compare against the published HTML as well as the
  PDF, and record such a defect in the allow file with its reason.
- **The contents need page numbers.** A PDF printed from HTML has none unless
  something writes them. The pipeline's PDF step and `render.sh` both do, and
  the gate's `pdf-toc-pages` check reports a PDF whose contents have none, or
  point at the wrong pages.
- **Tabs in code.** pandoc expands tabs to spaces unless told not to. The
  pipeline's HTML converter now passes `--preserve-tabs`; the gate's `html-code-sync`
  reports a published code block that is not the source's.

## Provenance

The converter is OASIS staff tooling (TC Administration), Apache-2.0 like the
rest of this repository's software. It is not a contribution to any TC's work
product. The Markdown it produces reproduces the TC's approved text without
technical change; the allow rules quote published OASIS Work Product text,
which keeps its own copyright (see NOTICE).
