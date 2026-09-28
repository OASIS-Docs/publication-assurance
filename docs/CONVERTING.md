<!--
Copyright (c) OASIS Open 2026. All Rights Reserved.

This document may be copied, published, and distributed to others without
restriction, provided it is reproduced verbatim and this notice is retained.
Author: Michael Coletta, Technical Advisor to OASIS Open.
-->

# Converting a specification to OASIS Markdown

This guide is for a TC whose published specification was written in DocBook
and which wants to write the next version in Markdown, in the OASIS Markdown
template that CSAF and NIEM use. It takes you from the DocBook source to a
Markdown file that says exactly what the published specification says, then
to a rendered and checked package, and then to the next stage. DMLex (LEXIDMA
TC) was the first specification converted this way. Every command below is
the one that converted it.

| Step | Tool | You get |
|---|---|---|
| 1. Convert | [`converters/docbook-to-markdown/build.sh`](../converters/docbook-to-markdown/README.md) | `<name>.md` and its figures |
| 2. Prove it matches | [`verify/verify_md.py`](../verify/README.md) | `RESULT: PASS`, and a report listing every difference and why it is accepted |
| 3. Render and check | [`render/render.sh`](../render/README.md) | HTML and PDF staged at their `docs.oasis-open.org` path, and the publication checks' verdict |
| 4. Prove the PDF matches | [`verify/verify_pdf.py`](../verify/README.md#verify_pdf-the-rendered-pdf-against-the-published-pdf) | `RESULT: PASS` against the published PDF: every word, the contents' page numbers, the running footer |
| 5. Review the pages | [`render/review_pairs.py`](../render/README.md#review_pairspy) | Published and rendered pages paired for a reviewer, with a planted fault, and a grade of the review |
| 6. Cut the next stage | [`pub-check/advance_stage.py`](../pub-check/README.md#cutting-the-next-stage) | `<name>` at the next stage, with every stage-bound line rewritten |

Word sources are not handled yet. Steps 2 to 6 do not depend on DocBook.
They work on any Markdown edition, however it was made.

## Before you start

You need Python 3.10 or later with the `beautifulsoup4` package
(`pip install beautifulsoup4`), pandoc 3.x, `xmllint`, Node.js 18 or later,
Chrome or Chromium, and poppler (`pdfinfo`, `pdftotext`). The converter needs
Graphviz and m4 if your specification generates figures the way DMLex does.
On Debian or Ubuntu:

```bash
sudo apt-get install libxml2-utils graphviz m4 poppler-utils
# pandoc: the .deb from https://github.com/jgm/pandoc/releases (the distribution's is too old)
```

Clone this repository at a release tag, and clone your TC's source:

```bash
git clone --depth 1 --branch v1.10.1 https://github.com/OASIS-Docs/publication-assurance
git clone https://github.com/oasis-tcs/lexidma
```

## 1. Convert

```bash
publication-assurance/converters/docbook-to-markdown/build.sh --profile dmlex \
    lexidma/dmlex-v1.0/specification dmlex-md \
    https://docs.oasis-open.org/lexidma/dmlex/v1.0/os/dmlex-v1.0-os.html
```

The converter reads your source tree and never writes to it. The output
directory gets `dmlex-v1.0-os.md`, every figure it references, and
`dmlex-v1.0-os-verification.json`. The last line printed is the verifier's
verdict (step 2).

A **profile** holds what is particular to one specification: its main file;
the file where the DocBook source names its version and stage; the output
name; whether key words are printed in capitals; the figure resolution; the
language label each kind of example file gets on its code block; and any
figure the TC's own build generates. DMLex's is
[`profiles/dmlex/`](../converters/docbook-to-markdown/profiles/dmlex/). For a
new specification, copy it, change what differs, and pass the directory to
`--profile`. The keys are listed in the
[converter's README](../converters/docbook-to-markdown/README.md#profiles).

If the converter stops with `UNHANDLED block <table>` (or another element),
your specification uses DocBook the converter does not handle yet. It stops
instead of flattening the element into paragraphs, which would keep the words
and lose the meaning. Ask TC Administration, or add the element to
`docbook2md.py` with a test.

## 2. Prove it matches

`build.sh` runs the verifier when you give it the published URL. You can also
run it on its own, against any Markdown edition:

```bash
python3 publication-assurance/verify/verify_md.py dmlex-md/dmlex-v1.0-os.md \
    https://docs.oasis-open.org/lexidma/dmlex/v1.0/os/dmlex-v1.0-os.html \
    --allow publication-assurance/converters/docbook-to-markdown/profiles/dmlex/allow.json \
    --json report.json
```

It compares both documents word for word, in order. It also compares:
- numbered headings;
- code blocks (byte for byte);
- list items, and tables cell by cell;
- image sources, in order;
- external link targets;
- struck-through and hidden text;
- internal anchors.

For DMLex it reports:

```
published_tokens: 61260
diff_regions: 0
accepted_deviations: 10
headings_missing: (0, [])
code_blocks_published: 316
code_blocks_markdown: 316
...
RESULT: PASS
```

**Reading a failure.** Each unexplained difference prints the words just
before it, then what the publication says and what the Markdown says:

```
[replace] ...DMLex is a data model for modelling
  PUB: dictionaries
  MD : lexicons
```

`replace` means the words changed, `delete` means the Markdown dropped them,
and `insert` means it added them. Fix the conversion, not the report.

**The allow file** is the complete list of the ways your Markdown is meant to
differ from the publication, each with a reason a reviewer can check. For
DMLex these are:
- template differences: "This stage" where DocBook said "This version", no
  "Specification URIs" heading, "Notices" as a heading rather than a label,
  and the Key words paragraph in its template position;
- the HTML page footer;
- two source defects in the published headings;
- the logo link;
- one bare URL that pandoc turns into a link.

A rule matches its difference exactly, once, unless it gives a `count`, and
only after the words in its `context` when it gives one. A rule that matches
nothing fails the run. That stops a paragraph that was allowed to move from
disappearing. Never add a rule to make a failure go away. Add one only for a
difference you would defend to the TC.

**Verify what is published, too.** The verifier reads your Markdown the way
GitHub displays it. The pipeline's HTML converter reads it with pandoc's own
Markdown dialect, which treats a few characters differently, and then applies
its own changes; that HTML is what is published. After step 3, check the
rendered HTML itself:

```bash
python3 publication-assurance/verify/verify_md.py out/lexidma/dmlex/v1.0/os/dmlex-v1.0-os.md \
    https://docs.oasis-open.org/lexidma/dmlex/v1.0/os/dmlex-v1.0-os.html \
    --rendered out/lexidma/dmlex/v1.0/os/dmlex-v1.0-os.html \
    --allow publication-assurance/converters/docbook-to-markdown/profiles/dmlex/allow.json \
    --allow publication-assurance/converters/docbook-to-markdown/profiles/dmlex/allow-rendered.json
```

This is how the pipeline was found turning the tab characters in 9 of DMLex's
316 code blocks into spaces. pub-check now checks the same thing for every package
(`html-code-sync`).

It also compares how each ordered list is numbered (`1`, `a`, `i`) and the
contents entry by entry. Both passed unseen in the first DMLex edition: its
section 2 lists were numbered `1.`, `2.` where the standard has `a.`, `b.`
(and its text says "as per point c. above"), and its contents stopped a
level short in the appendices. The words were the same, so no word
comparison could see either.

**What it cannot see:** a heading's level, a list item moved to another
level, emphasis removed. Read the Markdown diff for those, and use step 5.

## 3. Render and check

```bash
publication-assurance/render/render.sh dmlex-md lexidma/dmlex-v1.0/specification/schemas out
```

The stage path comes from the document's "This stage" URL, so the package is
laid out exactly as on `docs.oasis-open.org`
(`out/lexidma/dmlex/v1.0/os/`). The HTML comes from the pipeline's HTML
converter (TRANSFORMS.md, Stage 1). The PDF uses the pipeline's print styles
(Stage 2) and is printed by Chrome with the footer of a
published OASIS PDF: the name and track, the copyright line, the document's
date and the page. The table of contents gets its page numbers from the
printed pages. The last lines are the publication checks' findings. Exit 0 means
publishable. The pipeline's own PDF step, which prints with wkhtmltopdf,
produces the same footer and numbered contents.

A published specification being converted carries its own defects into the
checks. DMLex's nine blockers come from five defects, all in its source:
- `dmlex.nvh` is cited under the stage's own path but is missing from the
  TC's source repository, so the package lacks it (`asset-refs` and
  `package-refs`);
- one reference is a member-only URL (`member-uri`);
- two link texts end in `.pdf.pdf` while their targets end in `.pdf` (each
  reported twice, by the two `link-mismatch` conditions);
- two JSON schemas declare an `$id` that does not resolve (`schema-id`).

Record them for the TC to decide. Do not fix them in the conversion: the
conversion must say what the standard says.

## 4. Prove the PDF matches

```bash
python3 publication-assurance/verify/verify_pdf.py out/lexidma/dmlex/v1.0/os/dmlex-v1.0-os.pdf \
    https://docs.oasis-open.org/lexidma/dmlex/v1.0/os/dmlex-v1.0-os.pdf \
    --allow publication-assurance/converters/docbook-to-markdown/profiles/dmlex/allow-pdf.json
```

Step 2 checks HTML, and an HTML contents list has no page numbers. The first
DMLex renders printed their contents with none, where the published PDF
numbers every entry, and every HTML check passed them. `verify_pdf.py`
compares the two PDFs word for word, every page. A contents entry's number
is read as a placeholder, so the two editions may paginate differently, but
an entry numbered on one side only is a difference. The running footer is
compared too, and every rendered page must carry one.

For DMLex it passes with 42 accepted differences in 65,790 tokens (words
and punctuation marks), one block moved and one declared region (the UML
diagram, which Graphviz lays out anew). Most are the template's, as in step 2.
The rest are defects of the published PDF itself: its font has no `ň` or
`ō`, so it prints `sklize#` and `skul#` where the standard says `sklizeň` and
`skulō`, and where a page break splits Examples A.63, A.64, A.87 and A.88 it
prints the caption on a line of the example's code. Against the 24 September render it fails with
133 contents entries unnumbered.

## 5. Review the pages

The words are proven; how the pages look is not. A figure off the page, a
page number on the wrong line of a wrapped entry, a caption beside the wrong
block: these need a reviewer. A reviewer asked "do these match?" says yes.
The first DMLex comparison put the published and rendered contents pages
side by side, and nobody saw that one had no page numbers. So the review is
a task that cannot be passed by glancing:

```bash
python3 publication-assurance/render/review_pairs.py make \
    out/lexidma/dmlex/v1.0/os/dmlex-v1.0-os.pdf published.pdf pairs --key key.json
# give a reviewer pairs/PROMPT.md and the images in pairs/, never key.json
python3 publication-assurance/render/review_pairs.py grade key.json review.json
```

`make` pairs every page with a figure, the cover and the contents, plus 30
random pages, each with the published page that shares its words. It adds
one pair with something erased from the rendered side: the footer, a band of
text, or a contents page's numbers. The brief makes the reviewer copy lines
from both sides before comparing, and list every kind of element on each.

`grade` looks each copied line up in the text of its page, so a reviewer
that did not look is caught. It accepts the review only when the planted
fault is named for what it is. Pass the first review and then a re-run of
the pairs it failed; the later answers replace the earlier. On DMLex:
- Haiku copied lines that are not on the page for 21 of the 36 pairs and missed the fault;
- Sonnet named the fault and the `csd04.xml` heading defect. On two pairs it
  copied lines from other pages, and on three it copied too little to show
  it had read them (brackets, a heading). Those five were re-run, and the
  review was accepted.

A rejected review is run again. It is never read as a pass.

`render/compare.mjs` remains for a quick look at the HTML at named anchors.

## 6. Cut the next stage

DocBook keeps the version and stage in one place and fills them in
everywhere. A Markdown specification has no such variables, so its stage
lives in its text:
- the title version, the stage line and the date;
- the This, Previous and Latest stage URLs;
- the citation;
- every URL under its own stage path;
- the copyright year.

`advance_stage.py` rewrites all of them and counts each:

```bash
python3 publication-assurance/pub-check/advance_stage.py dmlex-md/dmlex-v1.0-os.md \
    --to wd01 --version 1.1 --previous source --date 2026-09-24 --unpublished-ok
# add --write to create dmlex-v1.1-wd01.md
```

- `--to` is the new stage and revision; `--version` is given only when the
  version changes.
- `--previous source` makes the document being cut the new "Previous stage";
  `--previous none` makes it N/A. A new version has to say which.
- `--unpublished-ok` is needed for a Working Draft (`wd`), because Working
  Drafts are not published on `docs.oasis-open.org` and their links will not
  resolve.
- The tool refuses a source file with uncommitted changes, so the cut can
  always be traced to a commit; `--allow-dirty` lifts that, and is only for a
  scratch copy you will throw away.

It is a dry run unless you add `--write`. It refuses, and writes nothing, when
anything is ambiguous. Its refusal rules are in the
[pub-check README](../pub-check/README.md#cutting-the-next-stage). Render and
check the result (step 3).

## Traps

- **Figure width.** A DocBook `<graphic contentwidth="16cm">` is sized by the
  stylesheet: 567 pixels at 90 dpi. Without an explicit width an SVG draws at
  its natural size, and the DMLex UML diagram ran off the page. The converter
  writes `<img width>` from the profile's `figure_dpi`.
- **Long inline code shrinks the PDF.** An unbreakable `code span` wider than
  the page makes a shrink-to-fit renderer print the whole document smaller.
  NIEM NDR v6.0 printed its 12pt body at 8pt. The pipeline's print styles wrap
  inline code, and pub-check's `pdf-legibility` check measures the printed body
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
  pub-check's `pdf-toc-pages` check reports a PDF whose contents have none, or
  point at the wrong pages.
- **Tabs in code.** pandoc expands tabs to spaces unless told not to. The
  pipeline's HTML converter now passes `--preserve-tabs`; pub-check's `html-code-sync`
  reports a published code block that is not the source's.

## Who owns what

The converter, verifier and renderer are OASIS staff tooling, licensed
Apache-2.0 (see [NOTICE](../NOTICE)). They are not a contribution to the TC's
work product. The Markdown edition reproduces the TC's approved text without
technical change. The TC owns it from the first commit.
