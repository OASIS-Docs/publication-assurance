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
GENERATED FILE: rendered from oasis_pub_check.py's condition registry by
render_checks_md.py. Edit the registry, not this file.
-->

# The OASIS publication acceptance criteria

**Author: Michael Coletta, Technical Advisor, OASIS Open**

This is the acceptance criteria set for publication on docs.oasis-open.org,
executable: every individual condition `oasis_pub_check.py` verifies, one row per condition:
what is checked, the value the tool pulls from the package, what that value
is compared against, and the severity if the condition fails. This file is
GENERATED from the tool's own condition registry by `render_checks_md.py`,
and `--list-checks` asserts the registry against the implementation every
time it runs, so the catalog cannot drift from the code.

The gate is input-format agnostic. A TC generates its own outputs from
whatever source format it authors in (Markdown, Word, ODT, DocBook/XML,
LaTeX, anything else), and what the gate validates is the output contract:
conformant HTML and PDF, with the authoritative source travelling beside
them. Conditions marked `md`, `docx`, or `odt` in the Applies column are add-ons
that engage only when that source format is present in the package; every
other condition runs on every package regardless of how it was authored.
A package that ships only its outputs still gets the full output and
package suites.

98 conditions across 35 check classes.

## Legend

| Field | Values |
|---|---|
| Severity | **BLOCKER**: the package cannot publish until fixed (exit 1). **WARN**: publishable, flagged for the record, often a must-fix before a later stage. **INFO**: recorded, no action required. |
| Applies | **both**: every package, regardless of input format. **md** / **docx** / **odt**: add-on conditions that engage only when that source format is present; on any other package they report NA with the reason, never a silent pass. There is no closed list of input formats: DocBook/XML, LaTeX, and any other source are validated through the **both** conditions, with the cover parsed from the rendered HTML. Deeper render-fidelity add-ons grow the same way the existing tracks did, calibrated against the published corpus. |
| Requires | A package or environment feature (network, `pdftotext`, `pdffonts`, shipped schemas, a shipped manifest) without which the condition reports NA in the validation report, never a silent pass. |

### asset-refs

Relative files the HTML references must ship in the package.

| # | Condition verified | Value pulled (observed) | Compared against | Severity | Applies | Requires |
|---|---|---|---|---|---|---|
| 1 | Every relative src/href the HTML references ships in the package | each package-relative src/href in the HTML (attribute values flattened across Word line wraps) | the package file tree; a missing target 404s on publication | BLOCKER | both | - |

### case

The publication host is case-sensitive; canonical paths are lowercase.

| # | Condition verified | Value pulled (observed) | Compared against | Severity | Applies | Requires |
|---|---|---|---|---|---|---|
| 2 | Every filename in the package is lowercase | every filename in the package tree | its lowercase form (the publication origin is case-sensitive; the canonical logo filename is exempt) | BLOCKER/WARN | both | - |
| 3 | Every self-referential docs.oasis-open.org URL path is lowercase (markdown source) | every docs.oasis-open.org URL in the prose (markdown source on the md track, rendered HTML on the DOCX track) | its lowercase form (case-sensitive origin; /templates/ paths exempt) | WARN | both | - |
| 4 | Every self-referential docs.oasis-open.org URL path is lowercase (HTML render) | every docs.oasis-open.org URL in the prose (markdown source on the md track, rendered HTML on the DOCX track) | its lowercase form (case-sensitive origin; /templates/ paths exempt) | WARN | both | - |

### cover-hr

A horizontal rule above the title opens the OASIS-rendered PDF with a blank page.

| # | Condition verified | Value pulled (observed) | Compared against | Severity | Applies | Requires |
|---|---|---|---|---|---|---|
| 5 | No horizontal rule between the OASIS logo and the title | the first 600 characters of the markdown | no --- / *** / ___ rule after the logo (the publication CSS renders it as a PDF page break) | WARN | md | - |

### date-sync

The markdown, HTML, and copyright dates must describe the same revision.

| # | Condition verified | Value pulled (observed) | Compared against | Severity | Applies | Requires |
|---|---|---|---|---|---|---|
| 6 | The markdown front-matter date appears in the HTML | the document date heading from the markdown | the rendered HTML text (absence means the HTML came from a different revision) | BLOCKER | md | - |
| 7 | The copyright year matches the document date year | the year in the OASIS copyright line | the year of the front-matter document date | WARN | md | - |

### dead-lists

Mail addresses at lists.oasis-open.org fail silently; comments go through Higher Logic.

| # | Condition verified | Value pulled (observed) | Compared against | Severity | Applies | Requires |
|---|---|---|---|---|---|---|
| 8 | No reference to a lists.oasis-open.org mailing address (markdown source) | every @lists.oasis-open.org address in the prose (markdown source on the md track, rendered HTML on the DOCX track) | the dead-infrastructure rule: that mail host silently fails; comments route via Higher Logic | BLOCKER | both | - |
| 9 | No reference to a lists.oasis-open.org mailing address (HTML render) | every @lists.oasis-open.org address in the prose (markdown source on the md track, rendered HTML on the DOCX track) | the dead-infrastructure rule: that mail host silently fails; comments route via Higher Logic | BLOCKER | both | - |
| 10 | Links into the retired list archives are flagged for verification | lists.oasis-open.org/archives links in the prose | each must be individually verified while the archive infrastructure is retired | WARN | md | - |

### double-slash

A double slash inside a relative path 404s on the CDN.

| # | Condition verified | Value pulled (observed) | Compared against | Severity | Applies | Requires |
|---|---|---|---|---|---|---|
| 11 | No relative link path contains a double slash | each relative link target in the prose | single slashes only (the CDN 404s a double slash even where browsers tolerate it) | BLOCKER | md | - |

### fence-collapse

An opening code fence with trailing text collapses the whole block under pandoc.

| # | Condition verified | Value pulled (observed) | Compared against | Severity | Applies | Requires |
|---|---|---|---|---|---|---|
| 12 | No opening code fence carries trailing text in its info string | each opening fence line's info string | a bare language token or curly-attribute form; trailing text collapses the block (lint D6) | BLOCKER | md | - |

### filenames

Delivery items are named for the published stage, one basename, all formats present.

| # | Condition verified | Value pulled (observed) | Compared against | Severity | Applies | Requires |
|---|---|---|---|---|---|---|
| 13 | The stage directory contains delivery items at all | the file listing of the stage directory root | at least one delivery item (md/docx/odt/html/pdf) must be present | BLOCKER | both | - |
| 14 | All delivery items share one basename | the set of delivery-item filename stems | exactly one distinct stem across md/docx/odt/html/pdf | BLOCKER | both | - |
| 15 | Delivery filename carries no working token | the delivery filename stem | forbidden working tokens: draft, tmp, rc (files are named for the published stage) | BLOCKER | both | - |
| 16 | Delivery filename ends in the stage suffix | the delivery filename stem | the stage directory name as a -&lt;stage&gt; suffix | BLOCKER | both | - |
| 17 | All required delivery formats are present | the set of delivery formats found in the package | the track's required set: html+pdf plus the authoritative source (md, docx, or odt) | BLOCKER | both | - |
| 18 | An authoritative source artifact travels with the renderings | the set of source formats found in the package root | at least one authoritative source (.md, .docx, or .odt) expected beside HTML/PDF | WARN | both | - |

### front-matter

The This/Latest stage URL blocks must match the package's real publish path.

| # | Condition verified | Value pulled (observed) | Compared against | Severity | Applies | Requires |
|---|---|---|---|---|---|---|
| 19 | Markdown front matter carries a This-stage URL block | URLs under the 'This Stage/Version' heading in the markdown | at least one URL must be declared | BLOCKER | md | - |
| 20 | Every stage URL is under docs.oasis-open.org | each URL in the This/Latest stage blocks | the canonical site prefix https://docs.oasis-open.org/ | BLOCKER | md | - |
| 21 | This-stage URLs carry the version and stage path segments | each URL in the This-stage block | the package's /&lt;version&gt;/ and /&lt;stage&gt;/ path segments | BLOCKER | md | - |
| 22 | Every This-stage URL points at a file shipped in the package | the filename each This-stage URL points at | the set of delivery filenames actually in the package | BLOCKER | md | - |
| 23 | The This-stage block lists all three artifacts (md, html, pdf) | the artifact extensions listed in the This-stage block | the full delivery set: .md, .html, .pdf | WARN | md | - |
| 24 | Latest-stage URLs point at the persistent version root | each URL in the Latest-stage block | must NOT contain the /&lt;stage&gt;/ segment (latest is the version-root path) | BLOCKER | md | - |
| 25 | Latest-stage URLs are under the package's version directory | each URL in the Latest-stage block | the package's /&lt;version&gt;/ path segment | BLOCKER | md | - |
| 26 | Any docs.oasis-open.org URL declaring a different version is intentional | every docs.oasis-open.org URL in the markdown outside Previous/Related-work blocks | the package's own version; a different version is a stale-draft tell unless external | WARN | md | - |
| 27 | No Latest-labelled line cites a stage-pinned URL for this spec | URLs on lines labelled 'Latest' in the prose | the persistent version-root form (no /&lt;stage&gt;/ segment) | BLOCKER | md | - |
| 28 | HTML cover carries a This-version URL block | URLs following 'This version/stage' on the rendered HTML cover | at least one URL must be present | BLOCKER | docx | - |
| 29 | Cover This-version URLs carry the version and stage segments | each URL in the cover's This-version block | the package's /&lt;version&gt;/ and /&lt;stage&gt;/ path segments | BLOCKER | docx | - |
| 30 | Cover Latest-version URLs point at the persistent version root | each URL in the cover's Latest-version block | must NOT contain the /&lt;stage&gt;/ segment | BLOCKER | docx | - |

### generator

DOCX-native renders must come from Microsoft Word, matching the TC's precedent.

| # | Condition verified | Value pulled (observed) | Compared against | Severity | Applies | Requires |
|---|---|---|---|---|---|---|
| 31 | A DOCX-native render was produced by Microsoft Word | the HTML Generator meta content | must contain 'Microsoft Word' (a LibreOffice render differs in kind from the TC's precedent) | BLOCKER | docx | - |

### html-anchors

Every internal fragment link must resolve to an anchor in the document.

| # | Condition verified | Value pulled (observed) | Compared against | Severity | Applies | Requires |
|---|---|---|---|---|---|---|
| 32 | Every internal fragment link resolves to an anchor | each internal href (#...) and the set of element ids/anchor names | every referenced fragment must exist as an id or &lt;a name&gt; | BLOCKER/WARN | both | - |
| 33 | The HTML carries a linked table of contents | the count of internal fragment links | at least one expected (a spec HTML without any is missing its TOC links) | WARN | both | - |

### html-residue

Pipeline residue in the HTML: duplicate title H1, stale pandoc header, CI paths.

| # | Condition verified | Value pulled (observed) | Compared against | Severity | Applies | Requires |
|---|---|---|---|---|---|---|
| 34 | No stale pandoc title-block header in the HTML | the HTML body | the &lt;header id="title-block-header"&gt; element must be absent (lint D2) | BLOCKER | both | - |
| 35 | No CI runner paths in HTML hrefs or srcs | every href/src attribute in the HTML | the /home/runner/ path prefix must not occur (lint D3) | BLOCKER | both | - |
| 36 | The document title appears in exactly one H1 | the count of &lt;h1&gt; elements matching the title text | exactly 1 (more renders the title twice on the PDF cover, lint D1) | BLOCKER | both | - |

### html-title

The HTML title element must be a real document title with no working residue.

| # | Condition verified | Value pulled (observed) | Compared against | Severity | Applies | Requires |
|---|---|---|---|---|---|---|
| 37 | HTML title carries no working residue | the &lt;title&gt; element text | must not end in tmp, draft, or wip | BLOCKER | both | - |
| 38 | HTML title is a plausible document title | the &lt;title&gt; element text and its length | a full spec title (at least 8 characters) | WARN | both | - |

### image-policy

Images must be self-contained, inert, and within the pipeline's size caps.

| # | Condition verified | Value pulled (observed) | Compared against | Severity | Applies | Requires |
|---|---|---|---|---|---|---|
| 39 | No empty img src attributes | each &lt;img&gt; tag's src attribute | src must be non-empty | BLOCKER | both | - |
| 40 | No absolute-path image sources | each &lt;img&gt; tag's src attribute | a leading / resolves outside the package on publication | BLOCKER | both | - |
| 41 | No path-traversal image sources | each &lt;img&gt; tag's src attribute | the path must not contain .. segments | BLOCKER | both | - |
| 42 | No responsive srcset image constructs | each &lt;img&gt; tag's attributes | the publication pipeline's self-containment policy refuses srcset | WARN | both | - |
| 43 | No &lt;picture&gt; elements | the HTML body | the publication pipeline's self-containment policy refuses &lt;picture&gt; | WARN | both | - |
| 44 | Every image file is under the per-image size cap | the byte size of each image file in the package | the pipeline's 2MB per-image refusal cap | WARN | both | - |
| 45 | No SVG carries script content | the body of each .svg file | &lt;script&gt; elements are active content, refused on docs.oasis-open.org | BLOCKER | both | - |
| 46 | No SVG carries inline event handlers | the body of each .svg file | on*= attributes are active content, refused | BLOCKER | both | - |
| 47 | No SVG references external image or use targets | the body of each .svg file | external &lt;image&gt;/&lt;use&gt; hrefs break self-containment | BLOCKER | both | - |
| 48 | Total image payload is under the cumulative cap | the summed byte size of all image files | the pipeline's 5MB cumulative inlining cap | WARN | both | - |

### junk-files

OS and editor junk must not ship in the package.

| # | Condition verified | Value pulled (observed) | Compared against | Severity | Applies | Requires |
|---|---|---|---|---|---|---|
| 49 | No working directories inside the package | every directory name in the package tree | forbidden set: __MACOSX, .git, .venv, venv, node_modules | BLOCKER | both | - |
| 50 | No OS junk or editor backup files in the package | every filename in the package tree | forbidden: .DS_Store, Thumbs.db, desktop.ini, and ~ / .bak / .orig / .swp suffixes | BLOCKER | both | - |

### link-mismatch

A visible URL and its link target must agree.

| # | Condition verified | Value pulled (observed) | Compared against | Severity | Applies | Requires |
|---|---|---|---|---|---|---|
| 51 | Visible URL text and its link target agree | each [shown-url](target-url) pair in the prose | shown and target must be the same URL (a disagreement is a rename artifact) | BLOCKER | md | - |

### logo

The cover logo should be the canonical OASIS template logo.

| # | Condition verified | Value pulled (observed) | Compared against | Severity | Applies | Requires |
|---|---|---|---|---|---|---|
| 52 | The cover logo is the canonical OASIS logo | each logo image source in the markdown | https://docs.oasis-open.org/templates/OASISLogo-v3.0.png | WARN | md | - |

### manifest

A shipped manifest.json must verify against the files on disk.

| # | Condition verified | Value pulled (observed) | Compared against | Severity | Applies | Requires |
|---|---|---|---|---|---|---|
| 53 | manifest.json parses as JSON | the manifest.json content | must parse without error | BLOCKER | both | manifest |
| 54 | Every manifest item exists in the package | each path listed in the manifest | the package file tree | BLOCKER | both | manifest |
| 55 | Every manifest sha256 matches the file's actual digest | the sha256 of each manifest-listed file | the digest recorded in the manifest | BLOCKER | both | manifest |

### md-links

Markdown link forms that render wrong under pandoc autolinking.

| # | Condition verified | Value pulled (observed) | Compared against | Severity | Applies | Requires |
|---|---|---|---|---|---|---|
| 56 | No dual [url](url) links in the markdown | every [text](target) link where text is itself a URL | text and target being the same URL calls for a bare autolink or real anchor text | WARN | md | - |
| 57 | No bare URL runs into '.\' without a space | each markdown line ending a URL with .\ | the safe form '. \' (otherwise pandoc pulls the period and backslash into the href) | BLOCKER | md | - |

### odt-integrity

The ODT source must be a valid, macro-free OpenDocument container.

| # | Condition verified | Value pulled (observed) | Compared against | Severity | Applies | Requires |
|---|---|---|---|---|---|---|
| 58 | The ODT source opens as a ZIP archive | the result of opening the .odt with the stdlib zip reader | a readable OpenDocument container | BLOCKER | odt | - |
| 59 | The ODT archive carries a mimetype member | the archive member listing | the OpenDocument package requirement of a mimetype entry | BLOCKER | odt | - |
| 60 | The declared mimetype is an OpenDocument type | the content of the mimetype member | the application/vnd.oasis.opendocument.* family | BLOCKER | odt | - |
| 61 | The ODT archive carries the document body (content.xml) | the archive member listing | the OpenDocument package requirement of a content.xml body | BLOCKER | odt | - |
| 62 | The ODT document body parses as XML | content.xml, parsed with the stdlib XML parser | well-formed XML | BLOCKER | odt | - |
| 63 | The ODT carries no embedded macros or scripts | archive member paths under Basic/ and Scripts/ | the host's active-content policy (none permitted, same as SVG scripts) | BLOCKER | odt | - |

### package-refs

Files the document cites under its own stage path must ship in the package.

| # | Condition verified | Value pulled (observed) | Compared against | Severity | Applies | Requires |
|---|---|---|---|---|---|---|
| 64 | Every file the document cites under its own stage path ships in the package | each cited URL under the this-stage base and the package file tree | the cited relative path must exist as a file in the package | BLOCKER | md | - |

### pdf-cover

The rendered PDF cover must carry the title exactly once and no CI paths.

| # | Condition verified | Value pulled (observed) | Compared against | Severity | Applies | Requires |
|---|---|---|---|---|---|---|
| 65 | The document title appears exactly once on the PDF cover page | the count of title occurrences in the PDF's first page text | exactly 1 (more means stale title-block residue baked into the render, assertion A1) | BLOCKER | both | pdftotext |
| 66 | No CI runner path anywhere in the PDF text | the full extracted PDF text | the /home/runner/ path must not occur (assertion A2) | BLOCKER | both | pdftotext |

### pdf-fonts

PDF embedded fonts are compared against the package's own CSS as typography authority.

| # | Condition verified | Value pulled (observed) | Compared against | Severity | Applies | Requires |
|---|---|---|---|---|---|---|
| 67 | pdffonts executes against the PDF | the pdffonts process outcome | a clean execution | WARN | both | pdffonts |
| 68 | The PDF's embedded fonts are declared by the package's own CSS | the font base names embedded in the PDF (pdffonts) | the font families declared in the package's HTML/CSS (its own typography authority) | WARN | both | pdffonts |

### pdf-sync

The PDF must be readable and rendered from the same revision as the rest of the package.

| # | Condition verified | Value pulled (observed) | Compared against | Severity | Applies | Requires |
|---|---|---|---|---|---|---|
| 69 | The PDF cross-check toolchain is available | the PATH lookup for pdftotext (poppler) | pdftotext present; absent means the PDF front-matter cross-check is skipped here and runs at intake | WARN | both | - |
| 70 | pdftotext executes against the PDF | the pdftotext process outcome | a clean execution | WARN | both | pdftotext |
| 71 | The PDF is machine-readable | pdftotext's exit status on the delivery PDF | exit 0 | BLOCKER | both | pdftotext |
| 72 | The PDF front matter carries the canonical this-stage URL | the first three pages of extracted PDF text | the this-stage base URL declared by the package front matter | BLOCKER | both | pdftotext |
| 73 | The PDF cites no unexpected other version of this spec | every this-spec version URL in the extracted PDF text | the package's own version (previous-stage citations expected, anything else confirmed) | WARN | both | pdftotext |

### previous-stage

Second and later stages must cite the previous stage's URLs.

| # | Condition verified | Value pulled (observed) | Compared against | Severity | Applies | Requires |
|---|---|---|---|---|---|---|
| 74 | A stage past 01 cites its previous stage | the URLs in the markdown's Previous-stage block | at least one docs.oasis-open.org URL required when the revision number exceeds 01 | BLOCKER | md | - |
| 75 | A stage past 01 cites its previous stage on the HTML cover | the URLs in the cover's Previous-version block | at least one docs.oasis-open.org URL required when the revision number exceeds 01 | BLOCKER | docx | - |

### residue

Editor placeholders (TODO, tbd, 'Will be filled in') must not ship.

| # | Condition verified | Value pulled (observed) | Compared against | Severity | Applies | Requires |
|---|---|---|---|---|---|---|
| 76 | No editor TODO markers left in prose | prose of the markdown and HTML (code blocks stripped) | the patterns TODO(...) and TODO: must not occur | BLOCKER | both | - |
| 77 | No bare 'tbd' placeholder sections | prose of the markdown and HTML (code blocks stripped) | no line consisting solely of 'tbd' | BLOCKER | both | - |
| 78 | No 'Will be filled in' placeholders (early-stage tolerated, must resolve before CS) | prose of the markdown and HTML (code blocks stripped) | the phrase 'Will be filled in' must not occur | WARN | both | - |

### revision-collision

A new submission must not collide with a stage already live for the version.

| # | Condition verified | Value pulled (observed) | Compared against | Severity | Applies | Requires |
|---|---|---|---|---|---|---|
| 79 | The submitted stage does not already exist on the live site | the HTTP status of the this-stage URL on docs.oasis-open.org | expected non-200 for a NEW submission; an existing stage means the revision must increment | WARN | both | network |

### rfc-keywords

Normative key words require the RFC 2119 (and 8174) citations.

| # | Condition verified | Value pulled (observed) | Compared against | Severity | Applies | Requires |
|---|---|---|---|---|---|---|
| 80 | Normative key words are backed by an RFC 2119 citation | normative key words (MUST, SHALL, SHOULD, MAY, ...) found in the prose | an RFC 2119 citation must be present when key words are used | BLOCKER | md | - |
| 81 | RFC 2119 citation is paired with RFC 8174 | the RFC citations in the document | the current template cites both 2119 and 8174 (uppercase-only clarification) | WARN | md | - |

### schema-id

Every JSON schema's $id must agree with where the file actually publishes.

| # | Condition verified | Value pulled (observed) | Compared against | Severity | Applies | Requires |
|---|---|---|---|---|---|---|
| 82 | Every .json file in the package parses as JSON | each .json file's content | must parse without error | BLOCKER | both | schemas |
| 83 | A flattened $id under the version root is a conscious convention | each schema's declared $id | the file's publish path; a version-root flattened $id (CSAF v2.0 style) needs a copy at that location | WARN | both | schemas |
| 84 | Each schema's $id agrees with where the file publishes | each schema's declared $id | the canonical latest-version URL derived from the package path | BLOCKER | both | schemas |
| 85 | Schema-internal self-references agree with the declared $id | every docs.oasis-open.org .json URL inside each schema body | the schema's own declared $id | BLOCKER | both | schemas |

### stage-name

The stage token must be a current, correctly numbered stage per the Naming Directives.

| # | Condition verified | Value pulled (observed) | Compared against | Severity | Applies | Requires |
|---|---|---|---|---|---|---|
| 86 | Stage directory name carries a two-digit revision number | the stage directory name | valid stage prefixes must carry a two-digit suffix (csd01, never bare csd) | BLOCKER | both | - |
| 87 | Stage token is not a retired abbreviation | the alphabetic prefix of the stage directory name | retired token set (csprd, cnprd, cos, csdpr, cndpr) per Naming Directives v1.7 | BLOCKER | both | - |
| 88 | Stage token is a recognized current stage | the alphabetic prefix of the stage directory name | valid stage set: wd, csd, cs, cnd, cn, os, ps, psd, pn, pnd, errata | BLOCKER | both | - |

### symlinks

Self-referential symlinks materialize into unbounded recursion on deploy.

| # | Condition verified | Value pulled (observed) | Compared against | Severity | Applies | Requires |
|---|---|---|---|---|---|---|
| 89 | No symlink points at itself or an ancestor directory | each symlink's resolved target | must not equal or contain its own directory (deploys materialize symlinks into unbounded recursion) | BLOCKER | both | - |

### template

The OASIS template's required front-matter sections, in order, plus Conformance.

| # | Condition verified | Value pulled (observed) | Compared against | Severity | Applies | Requires |
|---|---|---|---|---|---|---|
| 90 | All required template front-matter sections are present | the markdown headings | the template's required set: This/Previous/Latest stage, Technical Committee, Chairs, Editors, Abstract | BLOCKER | md | - |
| 91 | Front-matter sections appear in template order | the order of found front-matter sections | the canonical template ordering | WARN | md | - |
| 92 | A Conformance section exists | the markdown headings | the TC Process requirement: every Standards Track Work Product carries conformance clauses | BLOCKER | md | - |

### template-css

The HTML must carry a stylesheet; the canonical CSS is the default expectation.

| # | Condition verified | Value pulled (observed) | Compared against | Severity | Applies | Requires |
|---|---|---|---|---|---|---|
| 93 | A non-canonical stylesheet keeps the template font family | the primary font-family declared by the HTML's own stylesheet | the template look: Liberation Sans / Arial / Helvetica | WARN | md | - |
| 94 | The HTML carries a stylesheet | the HTML's &lt;link rel=stylesheet&gt; and &lt;style&gt; elements | at least one styling source must be present | BLOCKER | md | - |

### version-naming

The version directory and delivery filenames must agree on one vN.N(.N) version.

| # | Condition verified | Value pulled (observed) | Compared against | Severity | Applies | Requires |
|---|---|---|---|---|---|---|
| 95 | Version directory matches the vN.N(.N) convention | the version directory name from the package path | the Naming Directives version-segment pattern vN.N(.N), e.g. v1.0, v2.0.1 | BLOCKER | both | - |
| 96 | Version embedded in the delivery filename agrees with the version directory | the version segment embedded in the delivery filename stem | the version directory the package publishes under | BLOCKER | both | - |
| 97 | Delivery filename embeds the version segment | the delivery filename stem | the Naming Directives filename shape &lt;base&gt;-&lt;version&gt;-&lt;stage&gt; | WARN | both | - |

### vml-fallback

VML-only images in Word HTML renders are invisible in every modern browser.

| # | Condition verified | Value pulled (observed) | Compared against | Severity | Applies | Requires |
|---|---|---|---|---|---|---|
| 98 | Every VML image has an &lt;![if !vml]&gt; img fallback | the counts of v:imagedata elements and vml-fallback img tags | fallback count must cover VML count (the invisible-cover-logo class) | BLOCKER | both | - |

---

Generated from `oasis_pub_check.py` by `render_checks_md.py`. The inventory is
asserted from the code: `python3 oasis_pub_check.py --list-checks` fails if the
registry and the implementation disagree in either direction.

**The documentation set:** [Repository overview](../README.md) · [TC guide](../PUBLICATION-QUALITY.md) · [The acceptance criteria tool](README.md) · [Worked example](../examples/eox-core-v1.0-csd01/README.md) · [The pipeline, command by command](../TRANSFORMS.md) · [Architecture diagrams](../assets/architecture/README.md)
