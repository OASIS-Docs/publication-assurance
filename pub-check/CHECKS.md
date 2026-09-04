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
time it runs.

The gate is input-format agnostic. A TC generates its own outputs from
whatever source format it authors in (Markdown, Word, ODT, DocBook/XML,
LaTeX, anything else), and what the gate validates is the output contract:
conformant HTML and PDF, with the authoritative source travelling beside
them. Conditions marked `md`, `docx`, or `odt` in the Applies column are add-ons
that engage only when that source format is present in the package; every
other condition runs on every package regardless of how it was authored.
A package that includes only its outputs still gets the full output and
package suites.

170 conditions across 58 check classes.

## Legend

| Field | Values |
|---|---|
| Severity | **BLOCKER**: the package cannot publish until fixed (exit 1). **WARN**: publishable, flagged for the record, often a must-fix before a later stage. **INFO**: recorded, no action required. |
| Applies | **all**: runs on every package, whatever it was authored in. **md** / **docx** / **odt**: add-on conditions that engage only when the package carries that source format; on any other package they report NA with the reason rather than passing silently. A package authored in a format with no add-ons of its own (DocBook/XML, LaTeX, anything else) is validated through the **all** conditions, with the cover read from the rendered HTML. |
| Requires | A package or environment feature (network, `pdftotext`, `pdffonts`, packaged schemas, a packaged manifest) without which the condition reports NA in the validation report rather than passing silently. |

### artifact-naming

Non-document-identifier artifacts (schemas, images, WSDLs, codelists) should keep stable filenames across releases, not embed a stage/revision token.

| # | Condition verified | Value pulled (observed) | Compared against | Severity | Applies | Requires |
|---|---|---|---|---|---|---|
| 1 | A non-document-identifier artifact's own filename does not embed a stage+revision token | the full basename of every package file outside the delivery items, the delivery-stem-plus-recognized-suffix set (multi-part -partN-partName / public-review-metadata / comment-resolution-log, each restricted to the extensions a real prose side-file carries), and package-management files (manifest, checksum manifests, exact README/LICENSE variants, _audit/, OS junk) | Naming Directives s4: 'it is considered inadvisable to incorporate instance-specific [stage][revision] data for any release in filenames other than in the document identifier files ... thus mySchema.xsd but NOT mySchema-csd02.xsd'; TCs are advised to use named subdirectories and retain stable/identical filenames per s5.2/5.3's stage-abbreviation and two-digit-revision definitions | WARN | all | - |

### asset-refs

Relative files the HTML references must be included in the package.

| # | Condition verified | Value pulled (observed) | Compared against | Severity | Applies | Requires |
|---|---|---|---|---|---|---|
| 2 | Every relative src/href the HTML references is included in the package | each package-relative src/href in the HTML (attribute values flattened across Word line wraps) | the package file tree; a missing target 404s on publication | BLOCKER | all | - |

### authors

A Technical Report/Technical Report Draft must name one or more Authors on the cover page, distinct from a Committee Note's Editors listing.

| # | Condition verified | Value pulled (observed) | Compared against | Severity | Applies | Requires |
|---|---|---|---|---|---|---|
| 3 | A Technical Report/Technical Report Draft names its Authors on the cover page (heading or title-block byline) | a '## Authors'/'## Author(s)' heading (scoped to the front-matter window through Abstract), or a 'by &lt;Name&gt;' title-block byline (scoped to the title/type-label window), on a package whose cover-adjacent type label is Technical Report or Technical Report Draft | TC Handbook, Technical Reports: 'A Technical Report has one or more named Authors ... recorded on the cover page' | BLOCKER | md | - |
| 4 | The Authors heading/byline is not empty or placeholder-only (tbd/n/a/none), including list/task/blockquote-dressed variants | each line under the Authors heading (or the byline content), with list/task/blockquote markup and whitespace stripped | at least one non-placeholder named entry must remain | BLOCKER | md | - |
| 5 | A Technical Report Draft's Authors section is not left on the registry's own tolerated 'Will be filled in' placeholder indefinitely (WARN while still a TRD) | the Authors heading content (or byline content) when it normalizes to exactly the 'will be filled in' placeholder, on a package classified TRD | the existing residue-check precedent (check='residue') tolerating 'Will be filled in' pre-CS, scoped here to the Authors record of an in-progress Technical Report Draft | WARN | md | - |
| 6 | An approved (non-draft) Technical Report's Authors section is resolved, not still the 'Will be filled in' placeholder | the Authors heading content (or byline content) on a package classified as the final Technical Report (not TRD) | the TRD-stage 'will be filled in' tolerance does not survive Full Majority Vote approval to the final Technical Report | BLOCKER | md | - |

### boilerplate-dup

The template's comments/status boilerplate paragraph appears exactly once.

| # | Condition verified | Value pulled (observed) | Compared against | Severity | Applies | Requires |
|---|---|---|---|---|---|---|
| 7 | The template's 'send comments' status paragraph appears exactly once | the count of 'should send comments on this' occurrences in the prose | exactly one occurrence per the Board-approved template (a duplicate rides in on a stale template merge and truncates the sentence it collides with) | WARN | all | - |

### case

The publication host is case-sensitive; canonical paths are lowercase.

| # | Condition verified | Value pulled (observed) | Compared against | Severity | Applies | Requires |
|---|---|---|---|---|---|---|
| 8 | Every filename in the package is lowercase | every filename in the package tree | its lowercase form (the publication origin is case-sensitive; the canonical logo filename is exempt) | BLOCKER/WARN | all | - |
| 9 | Every self-referential docs.oasis-open.org URL path is lowercase (markdown source) | every docs.oasis-open.org URL in the prose (markdown source on the md track, rendered HTML on the DOCX track) | its lowercase form (case-sensitive origin; /templates/ paths exempt) | WARN | all | - |
| 10 | Every self-referential docs.oasis-open.org URL path is lowercase (HTML render) | every docs.oasis-open.org URL in the prose (markdown source on the md track, rendered HTML on the DOCX track) | its lowercase form (case-sensitive origin; /templates/ paths exempt) | WARN | all | - |

### comment-resolution-log

A comment-resolution log accompanying a CSD or CND public review must carry the exact basename the Naming Directives prescribe (BLOCKER if it is misnamed). Where the package itself shows the review concluded and no log-named file is present, the absence is flagged for confirmation (WARN). A near-miss is matched across hyphen and underscore word-joiners only, so a file that merely shares a word or two is not read as a misnamed log.

| # | Condition verified | Value pulled (observed) | Compared against | Severity | Applies | Requires |
|---|---|---|---|---|---|---|
| 11 | A file resembling a comment-resolution-log, if present in a CSD/CND stage directory that itself carries a public-review-metadata file, carries the exact basename Naming Directives prescribes | the sibling file listing of the stage directory root (immediate siblings of the document-identifier files only, per naming-directives.txt's 'directory with the CSD or CND' scoping); whether any sibling basename (extension stripped, hyphen/underscore-normalized) contains 'commentresolutionlog' without exactly matching the expected basename under a plausible-format extension | the expected basename [stem]-comment-resolution-log against naming-directives.txt s5.2's filename pattern for a produced comment resolution log | BLOCKER | all | - |
| 12 | Where in-package evidence (a later-stage sibling directory) shows a CSD/CND public review has demonstrably concluded, a comment-resolution-log basename match was sought and not found | the sibling file listing of the stage directory root; the presence of a later-stage sibling directory (cs/os/errata for a csd gate, cn for a cnd gate) alongside this stage directory, as the review-concluded closure signal | tc-process.txt s2.6/s2.7 (comment disposition is required to be posted to the TC's e-mail lists; the downstream approval ballot may only commence once every comment is resolved) against handbook-PublicReviews.txt's 'best practice, not a normative filing mandate' framing for HOW that record is kept | WARN | all | - |

### conformance-structure

Standards Track Conformance section structure: the section sits at top level rather than inside an Annex or subsection, each profile scope carries individually and uniquely numbered clauses, and from CS to OS the clause-number set is preserved exactly, with wording-only changes flagged for manual review.

| # | Condition verified | Value pulled (observed) | Compared against | Severity | Applies | Requires |
|---|---|---|---|---|---|---|
| 13 | At least one Conformance heading is a genuine top-level numbered section (not nested deeper than the document's modal top-level depth, and not under an Annex/Appendix ancestor) | every heading's nesting level, leading number prefix, and Annex/Appendix ancestor chain (markdown ATX headings, or rendered HTML h1-h6 on the DOCX-native track), with code-block content stripped first | handbook-Conformance.txt: 'a separate, top-level numbered section of the work product (not a subsection buried elsewhere)'; BLOCKER at cs/os (WARN at wd/csd, or when the modal-depth signal itself is low-confidence) | BLOCKER/WARN | all | - |
| 14 | Each conformance profile scope yields at least one extracted clause identifier | numbered sub-headings and paragraph-leading 'Clause N'/bracketed target-id labels within the Conformance section span, scoped per named profile | handbook-WPQualityRequirements.txt: 'a set of numbered conformance clauses to which any implementation must adhere'; BLOCKER at cs/os, WARN at wd/csd (fail-closed either way, so an empty section is reported rather than passing silently) | WARN | all | - |
| 15 | No clause identifier repeats within the same profile scope | the extracted clause-identifier set, scoped per named conformance profile (Core/Extended-style sub-headings matching 'Profile'/'Level') | handbook-Conformance.txt: 'individually numbered conformance clauses ... so that implementers and Statements of Use can cite specific clauses by number'; BLOCKER at cs/os, WARN at wd/csd | BLOCKER/WARN | all | - |
| 16 | Every (profile, clause number) pair in the previous stage is still present in this stage (append-only extension is fine; removal/renumbering, including a whole profile silently disappearing, is flagged) | the ((profile, clause number) -&gt; content hash) map extracted from the resolvable previous-stage artifact, diffed against this stage's map | handbook-WPQualityRequirements.txt 'Key principles': 'Clause numbering must be unique and stable across revisions'. Guidelines-sourced (recommended, not mandatory) so WARN-tier informational, never BLOCKER, and never fired for the CS-&gt;OS transition (that gets the zero-tolerance override instead) | WARN | all | - |
| 17 | A (profile, clause number) pair missing from this stage does not reappear under a DIFFERENT number in the same profile with the same content (a disguised renumber-via-delete-and-re-add) | content-hash collisions between a previous-stage clause and any current-stage clause, scoped within the same profile | the same Guidelines stability principle as 'removed/renumbered'; WARN-tier informational | WARN | all | - |
| 18 | At the CS-&gt;OS transition, the current (profile, clause id) key set is a byte-for-byte match to the approved-CS key set, scoped per profile, so a whole profile silently dropped while a surviving profile happens to reuse its bare clause numbers is still caught | the (profile, clause-identifier) sets extracted from the OS package and from the artifact named by its Previous-stage URI (verified to be the approved CS by stage token), each parsed with the extractor matching that artifact's own format (markdown or rendered HTML) | handbook-Conformance.txt 'OASIS Standard os': 'Conformance clauses are preserved unchanged from the approved Committee Specification' (TC Process 2.9): zero tolerance, always BLOCKER | BLOCKER | all | - |
| 19 | A clause whose (profile, number) key is unchanged at CS-&gt;OS is flagged for manual confirmation when its content hash changed | content-hash comparison, per (profile, clause number) key, between the approved CS and the OS package, restricted to keys present in both sets | handbook-WPQualityRequirements.txt 'Allowed changes during publication': coordinated non-material changes are permitted (TC Process 2.2.4); not itself a zero-tolerance failure, so WARN/manual-review, never an automatic BLOCKER | WARN | all | - |
| 20 | At the CS-&gt;OS transition, the approved-CS baseline artifact must be resolvable to verify clause-set preservation at all | the resolution outcome (local sibling stage directory, then network fetch) of the Previous-stage URI naming the approved CS | TC Process 2.9's preservation obligation cannot be verified for a Standards Track OS approval if the CS baseline is unreachable, so it is elevated to BLOCKER rather than reported as a silent WARN | BLOCKER | all | - |
| 21 | A general (non-CS-&gt;OS) stability diff that could not resolve its previous-stage artifact is visible in the report, not silently skipped | the resolution outcome of the Previous-stage URI | the general stability check is WARN-tier informational; an unresolvable prior artifact (first publication is a separate, silent no-op) still surfaces the gap as a WARN | WARN | all | - |

### content-labels

An Examples or Sample heading should carry an explicit non-normative or informative content-type label (WARN). Appendix and Annex headings get the same structural test, recorded as an advisory note that does not score.

| # | Condition verified | Value pulled (observed) | Compared against | Severity | Applies | Requires |
|---|---|---|---|---|---|---|
| 22 | Every Examples/Illustrative-Examples/Sample-&lt;noun&gt; heading carries a structural content-type label (heading suffix, first-sentence lead/predicate, labeled ancestor heading, or document-wide blanket statement) | markdown ATX/setext headings (or, DOCX-native track, rendered HTML h1-h6 elements via an HTMLParser walk, entities decoded), in document order, each with its heading text, nesting level, and the first sentence of the body block immediately following it | handbook-Conformance.txt 'Normative versus non-normative content': Examples content is classified non-normative and 'should be clearly labelled' | WARN | all | - |

### cover-hr

A horizontal rule above the title opens the OASIS-rendered PDF with a blank page.

| # | Condition verified | Value pulled (observed) | Compared against | Severity | Applies | Requires |
|---|---|---|---|---|---|---|
| 23 | No horizontal rule between the OASIS logo and the title | the first 600 characters of the markdown | no --- / *** / ___ rule after the logo (the publication CSS renders it as a PDF page break) | WARN | md | - |

### date-sync

The markdown, HTML, and copyright dates must describe the same revision.

| # | Condition verified | Value pulled (observed) | Compared against | Severity | Applies | Requires |
|---|---|---|---|---|---|---|
| 24 | The markdown front-matter date appears in the HTML | the document date heading from the markdown | the rendered HTML text (absence means the HTML came from a different revision) | BLOCKER | md | - |
| 25 | The copyright year matches the document date year | the year in the OASIS copyright line | the year of the front-matter document date | WARN | md | - |

### dead-lists

Mail addresses at lists.oasis-open.org fail silently; comments go through Higher Logic.

| # | Condition verified | Value pulled (observed) | Compared against | Severity | Applies | Requires |
|---|---|---|---|---|---|---|
| 26 | No reference to a lists.oasis-open.org mailing address (markdown source) | every @lists.oasis-open.org address in the prose (markdown source on the md track, rendered HTML on the DOCX track) | the dead-infrastructure rule: that mail host silently fails; comments route via Higher Logic | BLOCKER | all | - |
| 27 | No reference to a lists.oasis-open.org mailing address (HTML render) | every @lists.oasis-open.org address in the prose (markdown source on the md track, rendered HTML on the DOCX track) | the dead-infrastructure rule: that mail host silently fails; comments route via Higher Logic | BLOCKER | all | - |
| 28 | Links into the retired list archives are flagged for verification | lists.oasis-open.org/archives links in the prose | each must be individually verified while the archive infrastructure is retired | WARN | md | - |

### double-slash

A double slash inside a relative path 404s on the CDN.

| # | Condition verified | Value pulled (observed) | Compared against | Severity | Applies | Requires |
|---|---|---|---|---|---|---|
| 29 | No relative link path contains a double slash | each relative link target in the prose | single slashes only (the CDN 404s a double slash even where browsers tolerate it) | BLOCKER | md | - |

### extension-conformance

Principal and Multi-Part named-part filename extensions should match a common OASIS publication rendering format, not an invented or proprietary token.

| # | Condition verified | Value pulled (observed) | Compared against | Severity | Applies | Requires |
|---|---|---|---|---|---|---|
| 30 | Every root principal/stage-identifying filename and every Multi-Part named-part filename uses an extension that matches a common OASIS publication rendering format | the file extension token (lowercased, split on the last '.') of every root-level filename that shares the package's known delivery stem, and every filename anywhere in the package whose stem is that same delivery stem plus '-part&lt;N&gt;-&lt;partName&gt;' | a curated allowlist of common OASIS document/publication rendering-format extensions (txt, md, html, htm, pdf, doc, docx, odt, ods, odp, xls, xlsx, ppt, pptx, rtf, xml, json, epub), per Naming Directives Section 4 'File extensions should conform to industry best practice, matching well-known IANA MIME Media Types'; filenames on the Section 9 extensionless allowlist (CATALOG, catalog, README, ChangeLog) are exempt | WARN | all | - |

### extension-count

A delivery item must carry exactly one file extension after its document-identifier stem: BLOCKER, relaxed to WARN at wd stage (Naming Directives v1.7 s4/s9). The stem is subtracted only at a clean extension boundary, and the `tar.gz`, `tar.bz2` and `tar.xz` compounds count as one extension when the compound is the whole remaining suffix. Every other file in the package gets the same double-extension and missing-extension test as a non-blocking advisory.

| # | Condition verified | Value pulled (observed) | Compared against | Severity | Applies | Requires |
|---|---|---|---|---|---|---|
| 31 | A stage-directory-root delivery item (the established document-identifier stem plus one packaged format) carries at least one file extension | each delivery-item basename in items, with the 'filenames' check's already-validated shared stem subtracted from the front (only when the basename shares a clean extension boundary with the stem) | Naming Directives v1.7 s4: 'A single file(name) extension must be used in each filename except for a recognized set of extensionless filenames in common use.' BLOCKER at published stages, WARN at wd (s5.2 Note: working drafts 'may use any file naming pattern preferred by the TC'); wd-stage match is case-folded. | BLOCKER/WARN | all | - |
| 32 | A stage-directory-root delivery item carries exactly one file extension after the stem (or one blessed compound: tar.gz/tar.bz2/tar.xz, and only when that compound is the WHOLE remaining suffix) | each delivery-item basename in items, with the shared stem subtracted from the front, split into trailing dot-segments (empty segments from a malformed doubled/trailing dot are preserved, never silently dropped) | Naming Directives v1.7 s4's single-extension rule, structurally against the same stem boundary the 'filenames' check already validates. BLOCKER at published stages, WARN at wd. | BLOCKER/WARN | all | - |
| 33 | A non-delivery-item (Tier B) file with zero dots is one of the three literally recognized extensionless names | every file basename in the package tree outside the Tier A delivery-item set, junk-files' forbidden names and forbidden directories, and dotfiles | Naming Directives v1.7 s9: 'Exceptions to the rule that every filename must include a file extension include: CATALOG or catalog, README, ChangeLog.' Non-blocking WARN per s4's Applicability carve-out for non-identification-pattern files. | WARN | all | - |
| 34 | A non-delivery-item (Tier B) dotted filename's penultimate segment does not look like a known extension token (or the trailing pair is a blessed compound) | every dotted file basename in the package tree outside the Tier A delivery-item set, junk-files' forbidden names and forbidden directories, and dotfiles; its last two dot-segments | A disclosed, non-exhaustive known-extension-token vocabulary (not an IANA-derived classification); flagged only as a non-blocking heuristic pattern-match advisory per s4's Applicability carve-out for non-identification-pattern files (schemas, images, WSDLs, XML/JSON artifacts). | WARN | all | - |

### fence-collapse

An opening code fence with trailing text collapses the whole block under pandoc.

| # | Condition verified | Value pulled (observed) | Compared against | Severity | Applies | Requires |
|---|---|---|---|---|---|---|
| 35 | No opening code fence carries trailing text in its info string | each opening fence line's info string | a bare language token or curly-attribute form; trailing text collapses the block (lint D6) | BLOCKER | md | - |

### filenames

Delivery items are named for the published stage, one basename, all formats present.

| # | Condition verified | Value pulled (observed) | Compared against | Severity | Applies | Requires |
|---|---|---|---|---|---|---|
| 36 | The stage directory contains delivery items at all | the file listing of the stage directory root | at least one delivery item (md/docx/odt/html/pdf) must be present | BLOCKER | all | - |
| 37 | All delivery items share one basename | the set of delivery-item filename stems | exactly one distinct stem across md/docx/odt/html/pdf | BLOCKER | all | - |
| 38 | Delivery filename carries no working token | the delivery filename stem | forbidden working tokens: draft, tmp, rc (files are named for the published stage) | BLOCKER | all | - |
| 39 | Delivery filename ends in the stage suffix | the delivery filename stem | the stage directory name as a -&lt;stage&gt; suffix | BLOCKER | all | - |
| 40 | All required delivery formats are present | the set of delivery formats found in the package | the track's required set: html+pdf plus the authoritative source (md, docx, or odt) | BLOCKER | all | - |
| 41 | An authoritative source artifact travels with the renderings | the set of source formats found in the package root | at least one authoritative source (.md, .docx, or .odt) expected beside HTML/PDF | WARN | all | - |

### front-matter

The This/Latest stage URL blocks must match the package's actual publish path.

| # | Condition verified | Value pulled (observed) | Compared against | Severity | Applies | Requires |
|---|---|---|---|---|---|---|
| 42 | Markdown front matter carries a This-stage URL block | URLs under the 'This Stage/Version' heading in the markdown | at least one URL must be declared | BLOCKER | md | - |
| 43 | Every stage URL is under docs.oasis-open.org | each URL in the This/Latest stage blocks | the canonical site prefix https://docs.oasis-open.org/ | BLOCKER | md | - |
| 44 | This-stage URLs carry the version and stage path segments | each URL in the This-stage block | the package's /&lt;version&gt;/ and /&lt;stage&gt;/ path segments | BLOCKER | md | - |
| 45 | Every This-stage URL points at a file included in the package | the filename each This-stage URL points at | the set of delivery filenames actually in the package | BLOCKER | md | - |
| 46 | The This-stage block lists all three artifacts (md, html, pdf) | the artifact extensions listed in the This-stage block | the full delivery set: .md, .html, .pdf | WARN | md | - |
| 47 | Latest-stage URLs point at the persistent version root | each URL in the Latest-stage block | must NOT contain the /&lt;stage&gt;/ segment (latest is the version-root path) | BLOCKER | md | - |
| 48 | Latest-stage URLs are under the package's version directory | each URL in the Latest-stage block | the package's /&lt;version&gt;/ path segment | BLOCKER | md | - |
| 49 | Any docs.oasis-open.org URL declaring a different version is intentional | every docs.oasis-open.org URL in the markdown outside Previous/Related-work blocks | the package's own version; a different version is a stale-draft tell unless external | WARN | md | - |
| 50 | No Latest-labelled line cites a stage-pinned URL for this spec | URLs on lines labelled 'Latest' in the prose | the persistent version-root form (no /&lt;stage&gt;/ segment) | BLOCKER | md | - |
| 51 | HTML cover carries a This-version URL block | URLs following 'This version/stage' on the rendered HTML cover | at least one URL must be present | BLOCKER | docx | - |
| 52 | Cover This-version URLs carry the version and stage segments | each URL in the cover's This-version block | the package's /&lt;version&gt;/ and /&lt;stage&gt;/ path segments | BLOCKER | docx | - |
| 53 | Cover Latest-version URLs point at the persistent version root | each URL in the cover's Latest-version block | must NOT contain the /&lt;stage&gt;/ segment | BLOCKER | docx | - |

### generator

DOCX-native renders must come from Microsoft Word, matching the TC's precedent.

| # | Condition verified | Value pulled (observed) | Compared against | Severity | Applies | Requires |
|---|---|---|---|---|---|---|
| 54 | A DOCX-native render was produced by Microsoft Word | the HTML Generator meta content | must contain 'Microsoft Word' (a LibreOffice render differs in kind from the TC's precedent) | BLOCKER | docx | - |

### html-anchors

Every internal fragment link must resolve to an anchor in the document.

| # | Condition verified | Value pulled (observed) | Compared against | Severity | Applies | Requires |
|---|---|---|---|---|---|---|
| 55 | Every internal fragment link resolves to an anchor | each internal href (#...) and the set of element ids/anchor names | every referenced fragment must exist as an id or &lt;a name&gt; | BLOCKER/WARN | all | - |
| 56 | The HTML carries a linked table of contents | the count of internal fragment links | at least one expected (a spec HTML without any is missing its TOC links) | WARN | all | - |

### html-residue

Pipeline residue in the HTML: duplicate title H1, stale pandoc header, CI paths.

| # | Condition verified | Value pulled (observed) | Compared against | Severity | Applies | Requires |
|---|---|---|---|---|---|---|
| 57 | No stale pandoc title-block header in the HTML | the HTML body | the &lt;header id="title-block-header"&gt; element must be absent (lint D2) | BLOCKER | all | - |
| 58 | No CI runner paths in HTML hrefs or srcs | every href/src attribute in the HTML | the /home/runner/ path prefix must not occur (lint D3) | BLOCKER | all | - |
| 59 | The document title appears in exactly one H1 | the count of &lt;h1&gt; elements matching the title text | exactly 1 (more renders the title twice on the PDF cover, lint D1) | BLOCKER | all | - |

### html-title

The HTML title element must be an actual document title with no working residue.

| # | Condition verified | Value pulled (observed) | Compared against | Severity | Applies | Requires |
|---|---|---|---|---|---|---|
| 60 | HTML title carries no working residue | the &lt;title&gt; element text | must not end in tmp, draft, or wip | BLOCKER | all | - |
| 61 | HTML title is a plausible document title | the &lt;title&gt; element text and its length | a full spec title (at least 8 characters) | WARN | all | - |

### image-policy

Images must be self-contained, inert, and within the pipeline's size caps.

| # | Condition verified | Value pulled (observed) | Compared against | Severity | Applies | Requires |
|---|---|---|---|---|---|---|
| 62 | No empty img src attributes | each &lt;img&gt; tag's src attribute | src must be non-empty | BLOCKER | all | - |
| 63 | No absolute-path image sources | each &lt;img&gt; tag's src attribute | a leading / resolves outside the package on publication | BLOCKER | all | - |
| 64 | No path-traversal image sources | each &lt;img&gt; tag's src attribute | the path must not contain .. segments | BLOCKER | all | - |
| 65 | No responsive srcset image constructs | each &lt;img&gt; tag's attributes | the publication pipeline's self-containment policy refuses srcset | WARN | all | - |
| 66 | No &lt;picture&gt; elements | the HTML body | the publication pipeline's self-containment policy refuses &lt;picture&gt; | WARN | all | - |
| 67 | Every image file is under the per-image size cap | the byte size of each image file in the package | the pipeline's 2MB per-image refusal cap | WARN | all | - |
| 68 | No SVG carries script content | the body of each .svg file | &lt;script&gt; elements are active content, refused on docs.oasis-open.org | BLOCKER | all | - |
| 69 | No SVG carries inline event handlers | the body of each .svg file | on*= attributes are active content, refused | BLOCKER | all | - |
| 70 | No SVG references external image or use targets | the body of each .svg file | external &lt;image&gt;/&lt;use&gt; hrefs break self-containment | BLOCKER | all | - |
| 71 | Total image payload is under the cumulative cap | the summed byte size of all image files | the pipeline's 5MB cumulative inlining cap | WARN | all | - |

### junk-files

OS and editor junk must not be in the package.

| # | Condition verified | Value pulled (observed) | Compared against | Severity | Applies | Requires |
|---|---|---|---|---|---|---|
| 72 | No working directories inside the package | every directory name in the package tree | forbidden set: __MACOSX, .git, .venv, venv, node_modules | BLOCKER | all | - |
| 73 | No OS junk or editor backup files in the package | every filename in the package tree | forbidden: .DS_Store, Thumbs.db, desktop.ini, and ~ / .bak / .orig / .swp suffixes | BLOCKER | all | - |

### link-mismatch

A visible URL and its link target must agree.

| # | Condition verified | Value pulled (observed) | Compared against | Severity | Applies | Requires |
|---|---|---|---|---|---|---|
| 74 | Visible URL text and its link target agree | each [shown-url](target-url) pair in the prose | shown and target must be the same URL (a disagreement is a rename artifact) | BLOCKER | md | - |
| 75 | Anchor text that displays a URL agrees with the anchor's href | each &lt;a&gt; whose visible text is an absolute URL, paired with its href, from the rendered HTML | the displayed URL and the href must name the same resource (scheme, www., and trailing-slash differences and ellipsis display-truncation excepted); readers cite what they see | BLOCKER | all | - |

### logo

The cover logo should be the canonical OASIS template logo.

| # | Condition verified | Value pulled (observed) | Compared against | Severity | Applies | Requires |
|---|---|---|---|---|---|---|
| 76 | The cover logo is the canonical OASIS logo | each logo image source in the markdown | https://docs.oasis-open.org/templates/OASISLogo-v3.0.png | WARN | md | - |

### manifest

A packaged manifest.json must verify against the files on disk.

| # | Condition verified | Value pulled (observed) | Compared against | Severity | Applies | Requires |
|---|---|---|---|---|---|---|
| 77 | manifest.json parses as JSON | the manifest.json content | must parse without error | BLOCKER | all | manifest |
| 78 | Every manifest item exists in the package | each path listed in the manifest | the package file tree | BLOCKER | all | manifest |
| 79 | Every manifest sha256 matches the file's actual digest | the sha256 of each manifest-listed file | the digest recorded in the manifest | BLOCKER | all | manifest |

### md-links

Markdown link forms that render wrong under pandoc autolinking.

| # | Condition verified | Value pulled (observed) | Compared against | Severity | Applies | Requires |
|---|---|---|---|---|---|---|
| 80 | No dual [url](url) links in the markdown | every [text](target) link where text is itself a URL | text and target being the same URL calls for a bare autolink or real anchor text | WARN | md | - |
| 81 | No bare URL runs into '.\' without a space | each markdown line ending a URL with .\ | the safe form '. \' (otherwise pandoc pulls the period and backslash into the href) | BLOCKER | md | - |

### member-uri

No OASIS member-only (Kavi) URI may be cited in a public work product (Naming Directives v1.7 s6.6).

| # | Condition verified | Value pulled (observed) | Compared against | Severity | Applies | Requires |
|---|---|---|---|---|---|---|
| 82 | No OASIS member-only (Kavi) URI is cited in the package | every oasis-open.org /apps/org/ or /committees/download.php URL in the md and html | Naming Directives v1.7 s6.6: member-only (password-protected) Kavi references must not appear in public TC documents | BLOCKER | all | - |

### multi-part-naming

Multi-Part Work Product filenames must share one work-product abbreviation and version id (AC-NAMING-19) and, in a multi-part package, carry a well-formed, contiguously numbered `-partN-name` segment (AC-NAMING-20; Naming Directives v1.7 s4/s6.1). Scoped to Standards Track CSD/CS/OS and Non-Standards Track CND/CN stage directories.

| # | Condition verified | Value pulled (observed) | Compared against | Severity | Applies | Requires |
|---|---|---|---|---|---|---|
| 83 | Every Multi-Part Work Product part filename embeds the identical WP-abbrev token | the WP-abbrev token from every stage-root and part-subdirectory filename matching the Multi-Part Naming Directives grammar (&lt;WP-abbrev&gt;-&lt;version-id&gt;-&lt;stage-abbrev&gt;&lt;rev&gt;-part&lt;N&gt;-&lt;partName&gt;) | the set of distinct WP-abbrev tokens across all matched part filenames must collapse to exactly one value, per TC Process 2.2.3's single Work Product name and the Handbook's Multi-part work products restatement | BLOCKER | all | - |
| 84 | Every Multi-Part Work Product part filename embeds the identical version-id token | the version-id token from every stage-root and part-subdirectory filename matching the Multi-Part Naming Directives grammar (&lt;WP-abbrev&gt;-&lt;version-id&gt;-&lt;stage-abbrev&gt;&lt;rev&gt;-part&lt;N&gt;-&lt;partName&gt;) | the set of distinct version-id tokens across all matched part filenames must collapse to exactly one value, per TC Process 2.2.3's single Work Product version number and the Handbook's Multi-part work products restatement | BLOCKER | all | - |
| 85 | No bare CORE.ext delivery filename coexists with genuine part files | delivery-item stems sharing one &lt;wp&gt;-&lt;version&gt;-&lt;stage&gt; core, and their tails | naming-directives.txt s4: the single-part bare-CORE filename rule does not apply once the package is multi-part | BLOCKER | all | - |
| 86 | Every non-canonical delivery filename sharing the package core carries a well-formed -part&lt;N&gt;-&lt;name&gt; segment | the tail (text after the resolved &lt;wp&gt;-&lt;version&gt;-&lt;stage&gt; core) of each in-scope delivery filename | Naming Directives v1.7 s4 multi-part filename grammar: literal lowercase 'part' + Arabic numeral + hyphen + partName, positioned before the extension | BLOCKER | all | - |
| 87 | A part file discovered inside an Option-1 URI part-subdirectory agrees with that subdirectory's own [partNumber]-[partName] segment | the part number/name parsed from the filename tail and from its containing part-subdirectory name | naming-directives.txt s6.1 (Option 1): the subdirectory segment and the filename's part identifier must name the same part | BLOCKER | all | - |
| 88 | Each part number maps to exactly one partName across every format variant and discovery location | the (number, partName) pairs extracted from every in-scope filename tail | Naming Directives v1.7 s4: partNumber identifies one distinct separately-titled prose part, not two | BLOCKER | all | - |
| 89 | Part numbering for a multi-part package begins at 1 | the sorted set of unique part numbers found across the package's in-scope delivery filenames | naming-directives.txt s4: partNumber begins with the number '1' (for Part 1) | BLOCKER | all | - |
| 90 | Part numbering for a multi-part package is contiguous with no gaps | the sorted set of unique part numbers found across the package's in-scope delivery filenames | naming-directives.txt s4: partNumber increases monotonically (2, 3, 4, ...) for other parts, i.e. the exact sequence [1, 2, ..., N] | BLOCKER | all | - |

### name-chars

Every filename and directory name must stay within the sixty-four permitted characters. UNDERSCORE is a BLOCKER in an identifying (document-URI) name and a WARN elsewhere. An empty identifying name is a BLOCKER.

| # | Condition verified | Value pulled (observed) | Compared against | Severity | Applies | Requires |
|---|---|---|---|---|---|---|
| 91 | No underscore in an identifying (document-URI-bearing) package name | the stage directory name, the version directory name, each stage-root delivery-item filename sharing the package's established basename, and any Multi-Part partN-name directory/file | STRICT allowlist [A-Za-z0-9.-]. Naming Directives v1.7 s3: an UNDERSCORE 'must never be used in a filename or directory name that is used in a document URI' | BLOCKER | all | - |
| 92 | No character outside the sixty-four permitted characters in an identifying package name | the stage directory name, the version directory name, each stage-root delivery-item filename sharing the package's established basename, and any Multi-Part partN-name directory/file | STRICT allowlist [A-Za-z0-9.-]. Naming Directives v1.7 s3: 'TCs must use only the sixty-four characters from among alphanumerics [A-Za-z0-9] and the two punctuation characters ... PERIOD ... and ... HYPHEN' | BLOCKER | all | - |
| 93 | No character outside the sixty-four permitted characters plus UNDERSCORE in a supporting (non-identifying) package name | every filename and directory basename in the package tree outside the identifying set | BASE allowlist [A-Za-z0-9._-]. Naming Directives v1.7 s3 base 'must use only' clause, with UNDERSCORE included per the conditional tolerance | BLOCKER | all | - |
| 94 | An identifying (document-URI-bearing) package name is non-empty | the stage directory name, the version directory name, each stage-root delivery-item filename sharing the package's established basename, and any Multi-Part partN-name directory/file | STRICT test ^[A-Za-z0-9.-]+$: the '+' quantifier requires at least one character, so an empty identifying name trivially fails the sixty-four-permitted-character allowlist; mirrors how check_stage_name's and check_version_naming's own fullmatch patterns already reject an empty stage/version token without any special-casing | BLOCKER | all | - |

### normdef-refs

Every packaged normative schema/grammar/code file (Standards Track) must be referenced from the Work Product (TC Process 2.2.5).

| # | Condition verified | Value pulled (observed) | Compared against | Severity | Applies | Requires |
|---|---|---|---|---|---|---|
| 95 | Every candidate normative-definition file (schema/grammar/code plain-text file, excluding example/sample/test-case/non-normative and pipeline/asset directories) is referenced from the Work Product | each candidate file's package-relative path and basename, tested via structured link/href/src/schemaLocation/$ref target extraction (path-level, then basename-level) against the spec's own text (or rendered HTML on the DOCX track), every OTHER candidate file's own content and extracted targets, and manifest.json (package root only)/top-level README-or-index text, all normalized (URL-decode, Unicode NFC) | TC Process 2.2.5: 'Each text file must be referenced from the Work Product; and'. Standards Track (csd, cs, os, errata) only | BLOCKER | all | - |
| 96 | A basename-only match among candidate files sharing that basename in different directories is flagged for confirmation rather than silently satisfying the requirement for every tied file | candidate files sharing an identical basename in different package directories, and whether any reference to that basename in the corpus is path-qualified | TC Process 2.2.5's reference requirement; an ambiguous basename-only match does not unambiguously resolve which file was referenced | WARN | all | - |

### ns-segment

This/Latest-stage cover URIs must not reuse the reserved /ns/ path segment (namespace identifiers only); Previous-stage hits are WARN (inherited, immutable citation).

| # | Condition verified | Value pulled (observed) | Compared against | Severity | Applies | Requires |
|---|---|---|---|---|---|---|
| 97 | This-stage and Latest-stage cover URIs do not reuse the reserved /ns/ path segment | the This-stage and Latest-stage URL(s) from the markdown front matter (md track) or the rendered HTML cover (docx-native track, via the shared html_cover_urls() helper) | handbook-Naming.txt: '/ns/ ... is for namespace identifiers, not for retrievable documents. Do not use /ns/ in the URI of a document you intend to publish as a retrievable resource' | BLOCKER | all | - |
| 98 | Previous-stage cover URI does not reuse the reserved /ns/ path segment (non-blocking, manual-review if it does: an immutable inherited citation) | the Previous-stage URL from the markdown front matter (md track) or the rendered HTML cover (docx-native track, via the shared html_cover_urls() helper) | handbook-Naming.txt's /ns/ reservation rule, applied to an already-published prior-stage citation the current package cannot alter | WARN | all | - |

### odt-integrity

The ODT source must be a valid, macro-free OpenDocument container.

| # | Condition verified | Value pulled (observed) | Compared against | Severity | Applies | Requires |
|---|---|---|---|---|---|---|
| 99 | The ODT source opens as a ZIP archive | the result of opening the .odt with the stdlib zip reader | a readable OpenDocument container | BLOCKER | odt | - |
| 100 | The ODT archive carries a mimetype member | the archive member listing | the OpenDocument package requirement of a mimetype entry | BLOCKER | odt | - |
| 101 | The declared mimetype is an OpenDocument type | the content of the mimetype member | the application/vnd.oasis.opendocument.* family | BLOCKER | odt | - |
| 102 | The ODT archive carries the document body (content.xml) | the archive member listing | the OpenDocument package requirement of a content.xml body | BLOCKER | odt | - |
| 103 | The ODT document body parses as XML | content.xml, parsed with the stdlib XML parser | well-formed XML | BLOCKER | odt | - |
| 104 | The ODT carries no embedded macros or scripts | archive member paths under Basic/ and Scripts/ | the host's active-content policy (none permitted, same as SVG scripts) | BLOCKER | odt | - |

### package-refs

Files the document cites under its own stage path must be included in the package.

| # | Condition verified | Value pulled (observed) | Compared against | Severity | Applies | Requires |
|---|---|---|---|---|---|---|
| 105 | Every file the document cites under its own stage path is included in the package | each cited URL under the this-stage base and the package file tree | the cited relative path must exist as a file in the package | BLOCKER | md | - |

### pdf-cover

The rendered PDF cover must carry the title exactly once and no CI paths.

| # | Condition verified | Value pulled (observed) | Compared against | Severity | Applies | Requires |
|---|---|---|---|---|---|---|
| 106 | The document title appears exactly once on the PDF cover page | the count of title occurrences in the PDF's first page text | exactly 1 (more means stale title-block residue baked into the render, assertion A1) | BLOCKER | all | pdftotext |
| 107 | No CI runner path anywhere in the PDF text | the full extracted PDF text | the /home/runner/ path must not occur (assertion A2) | BLOCKER | all | pdftotext |

### pdf-fonts

PDF embedded fonts are compared against the package's own CSS as typography authority.

| # | Condition verified | Value pulled (observed) | Compared against | Severity | Applies | Requires |
|---|---|---|---|---|---|---|
| 108 | pdffonts executes against the PDF | the pdffonts process outcome | a clean execution | WARN | all | pdffonts |
| 109 | The PDF's embedded fonts are declared by the package's own CSS | the font base names embedded in the PDF (pdffonts) | the font families declared in the package's HTML/CSS (its own typography authority) | WARN | all | pdffonts |

### pdf-sync

The PDF must be readable and rendered from the same revision as the rest of the package.

| # | Condition verified | Value pulled (observed) | Compared against | Severity | Applies | Requires |
|---|---|---|---|---|---|---|
| 110 | The PDF cross-check toolchain is available | the PATH lookup for pdftotext (poppler) | pdftotext present; absent means the PDF front-matter cross-check is skipped here and runs at intake | WARN | all | - |
| 111 | pdftotext executes against the PDF | the pdftotext process outcome | a clean execution | WARN | all | pdftotext |
| 112 | The PDF is machine-readable | pdftotext's exit status on the delivery PDF | exit 0 | BLOCKER | all | pdftotext |
| 113 | The PDF front matter carries the canonical this-stage URL | the first three pages of extracted PDF text | the this-stage base URL declared by the package front matter | BLOCKER | all | pdftotext |
| 114 | The PDF cites no unexpected other version of this spec | every this-spec version URL in the extracted PDF text | the package's own version (previous-stage citations expected, anything else confirmed) | WARN | all | pdftotext |

### previous-stage

Second and later stages must cite the previous stage's URLs.

| # | Condition verified | Value pulled (observed) | Compared against | Severity | Applies | Requires |
|---|---|---|---|---|---|---|
| 115 | A stage past 01 cites its previous stage | the URLs in the markdown's Previous-stage block | at least one docs.oasis-open.org URL required when the revision number exceeds 01 | BLOCKER | md | - |
| 116 | A stage past 01 cites its previous stage on the HTML cover | the URLs in the cover's Previous-version block | at least one docs.oasis-open.org URL required when the revision number exceeds 01 | BLOCKER | docx | - |

### public-review-metadata

Post-publication audit: a csd/cnd stage directory that underwent a TC public review must carry the [WP-abbrev]-[version-id]-[stage-abbrev][revisionNumber]-public-review-metadata.html companion file Project Administration is obligated to publish alongside it (Naming Directives v1.7 s5.2 / TC Handbook Naming).

| # | Condition verified | Value pulled (observed) | Compared against | Severity | Applies | Requires |
|---|---|---|---|---|---|---|
| 117 | A live, published csd/cnd stage directory confirmed (by tiered evidence) and successfully scanned to have undergone TC public review carries the required public-review-metadata companion file | the LIVE docs.oasis-open.org stage-directory-root filename listing (fetched over the network, post-publication audit only), plus a same-revision comment-resolution-log or a downstream cs/errata stage's own Previous-stage cover URL as evidence the review occurred | the exact, case-sensitive filename [WP-abbrev]-[version-id]-[stage-abbrev][revisionNumber]-public-review-metadata.html (naming-directives.txt 5.2; handbook-Naming.txt 'Public-review metadata filename (new in v1.7)') | BLOCKER | all | - |
| 118 | A present public-review-metadata companion file is non-empty | the byte length of the fetched companion file | naming-directives.txt 5.2: the file 'provides a publication history of the Work Product' (content validation itself is out of scope for this check; only non-zero size is tested here) | WARN | all | - |
| 119 | A public-review-metadata companion file listed in the live directory is actually reachable so its content can be evaluated | the HTTP status of a direct fetch of the listed companion filename | a listing entry alone is not proof of a readable file; an unreachable listed file stays an open advisory rather than a silent, unreviewed pass | WARN | all | - |

### ref-rfc

An [RFCnnnn] references entry's label, body text, and URL must cite the same RFC number.

| # | Condition verified | Value pulled (observed) | Compared against | Severity | Applies | Requires |
|---|---|---|---|---|---|---|
| 120 | An [RFCnnnn] references entry's URL cites the same RFC number as its label | each RFC number embedded in an ietf.org / rfc-editor.org URL inside the entry window that follows an [RFCnnnn] label | the RFC number in the entry's own label; a disagreement means the label or the linked document is stale | WARN | all | - |
| 121 | An [RFCnnnn] references entry's body text cites the same RFC number as its label and URL | each 'RFC nnnn' mention in the entry window that follows an [RFCnnnn] label, excluding mentions excused by obsoletes/supersedes/replaces/updates/see phrasing | the RFC number in the entry's label and URL (numbers drift when a reference is upgraded to a successor RFC and the prose is not) | WARN | all | - |

### references-split

On a Standards Track work product, Normative and Informative References should be separately labeled, with no reference ID listed under both (handbook-WPQualityChecklist.txt, WARN).

| # | Condition verified | Value pulled (observed) | Compared against | Severity | Applies | Requires |
|---|---|---|---|---|---|---|
| 122 | A bare 'References' heading carrying 2+ direct reference entries is split into separately labeled Normative/Informative child headings (or is too small a sample, 0 or 1 entries, to judge) | H1-H3 headings normalizing to 'references' plus the distinct reference-entry IDs found directly in that heading's own span (before its first immediate-child heading) | handbook-WPQualityChecklist.txt editorial quality checklist bullet: 'normative references listed separately from informative references' (WARN: staff-maintained best-practice checklist, not a TC Process must/shall clause) | WARN | all | - |
| 123 | No reference-entry ID appears under both a Normative References heading and an Informative References heading anywhere in the document | the set of reference-entry IDs found in the span of every 'normative references'-classified heading, and the same for every 'informative references'-classified heading | the two ID sets must not intersect; a shared ID is a labeling inconsistency or editorial duplication (handbook-WPQualityChecklist.txt same checklist bullet) | WARN | all | - |

### residue

Editor placeholders (TODO, tbd, 'Will be filled in') must not be present.

| # | Condition verified | Value pulled (observed) | Compared against | Severity | Applies | Requires |
|---|---|---|---|---|---|---|
| 124 | No editor TODO markers left in prose | prose of the markdown and HTML (code blocks stripped) | the patterns TODO(...) and TODO: must not occur | BLOCKER | all | - |
| 125 | No bare 'tbd' placeholder sections | prose of the markdown and HTML (code blocks stripped) | no line consisting solely of 'tbd' | BLOCKER | all | - |
| 126 | No template editor-instruction text left in the published prose | prose of the markdown and HTML (code blocks stripped) | the OASIS Board-approved work product templates, which state that 'All template instructions ... need to be deleted prior to publication'; an imperative to remove/delete something 'before publication' or 'prior to publication' surviving in the prose means an instruction block reached publication | BLOCKER | all | - |
| 127 | No 'Will be filled in' placeholders (early-stage tolerated, must resolve before CS) | prose of the markdown and HTML (code blocks stripped) | the phrase 'Will be filled in' must not occur | WARN | all | - |

### revision-collision

A new submission must not collide with a stage already live for the version.

| # | Condition verified | Value pulled (observed) | Compared against | Severity | Applies | Requires |
|---|---|---|---|---|---|---|
| 128 | The submitted stage does not already exist on the live site | the HTTP status of the this-stage URL on docs.oasis-open.org | expected non-200 for a NEW submission; an existing stage means the revision must increment | WARN | all | network |

### rfc-keywords

Normative key words require the RFC 2119 (and 8174) citations.

| # | Condition verified | Value pulled (observed) | Compared against | Severity | Applies | Requires |
|---|---|---|---|---|---|---|
| 129 | Normative key words are backed by an RFC 2119 citation | normative key words (MUST, SHALL, SHOULD, MAY, ...) found in the prose | an RFC 2119 citation must be present when key words are used | BLOCKER | md | - |
| 130 | RFC 2119 citation is paired with RFC 8174 | the RFC citations in the document | the current template cites both 2119 and 8174 (uppercase-only clarification) | WARN | md | - |

### schema-id

Every JSON schema's $id must agree with where the file actually publishes.

| # | Condition verified | Value pulled (observed) | Compared against | Severity | Applies | Requires |
|---|---|---|---|---|---|---|
| 131 | Every .json file in the package parses as JSON | each .json file's content | must parse without error | BLOCKER | all | schemas |
| 132 | A flattened $id under the version root is a conscious convention | each schema's declared $id | the file's publish path; a version-root flattened $id (CSAF v2.0 style) needs a copy at that location | WARN | all | schemas |
| 133 | Each schema's $id agrees with where the file publishes | each schema's declared $id | the canonical latest-version URL derived from the package path | BLOCKER | all | schemas |
| 134 | Schema-internal self-references agree with the declared $id | every docs.oasis-open.org .json URL inside each schema body | the schema's own declared $id | BLOCKER | all | schemas |

### stage-name

The stage token must be a current, correctly numbered stage per the Naming Directives.

| # | Condition verified | Value pulled (observed) | Compared against | Severity | Applies | Requires |
|---|---|---|---|---|---|---|
| 135 | Stage directory name carries a two-digit revision number | the stage directory name | valid stage prefixes must carry a two-digit suffix (csd01, never bare csd) | BLOCKER | all | - |
| 136 | Stage token is not a retired abbreviation | the alphabetic prefix of the stage directory name | retired token set (csprd, cnprd, cos, csdpr, cndpr) per Naming Directives v1.7 | BLOCKER | all | - |
| 137 | Stage token is a recognized current stage | the alphabetic prefix of the stage directory name | valid stage set: wd, csd, cs, cnd, cn, os, ps, psd, pn, pnd, errata | BLOCKER | all | - |

### stage-token

On a second or later stage, the Previous-stage cover URI should carry the document's own csd or cnd stage token; a retired or mismatched token is a WARN, with a caveat for pre-v1.7 legacy paths. A Latest-stage cover URI filename must embed no stage-abbreviation or revision token at all (BLOCKER; whether it matches is beside the point). Tokens are read after percent-decoding, tolerate surrounding prose punctuation, and split on '-' and '.', so a filename that joins the version and stage with a period still yields its token.

| # | Condition verified | Value pulled (observed) | Compared against | Severity | Applies | Requires |
|---|---|---|---|---|---|---|
| 138 | Previous-stage URL stage token is not a retired abbreviation | the stage-abbreviation token extracted from the Previous-stage URL's directory segment and/or filename stem | retired token set (csprd, cnprd, cos, csdpr, cndpr) per Naming Directives v1.7; WARN with a legacy-URI verification caveat since a pre-2024 Previous-stage URI may permanently retain a retired token (naming-directives.txt 6.3 Resource Permanence) | WARN | all | - |
| 139 | Previous-stage URL stage token matches the document's own current csd/cnd stage abbreviation or the track's approved-stage counterpart | the stage-abbreviation token extracted from the Previous-stage URL's directory segment and/or filename stem | the document's own current stage token, or the track's approved-stage set (csd: cs/os/errata; cnd: cn) when the block links a previous VERSION at its own approved stage (handbook-PublicReviews.txt: the cover page URIs 'should all reflect the csd stage abbreviation') | WARN | all | - |
| 140 | Latest-stage URL's filename embeds no stage-abbreviation/revision token at all | the filename-stem-position stage-abbreviation token (if any) extracted from the Latest-stage URL | naming-directives.txt 6.2: the Latest-stage locator URI 'does not contain the path component [stage-abbrev][revisionNumber] or stage identifier in the filename', an absolute prohibition independent of whether the token matches the current stage | BLOCKER | all | - |

### stage-uri-live

The Previous-stage and Latest-stage URIs on the cover name files that are not in the package, so every other check can see only their shape. This class fetches them. A 404 or 410 is a BLOCKER: the cover cites a document that was never published at that address, usually because the template hardcodes the extension while templating the stage name, so a stage that went markdown-native is still cited as `.docx`. Transport failures, 5xx responses and bot challenges are recorded as INFO. `PUB_CHECK_OFFLINE` turns the class off.

| # | Condition verified | Value pulled (observed) | Compared against | Severity | Applies | Requires |
|---|---|---|---|---|---|---|
| 141 | Every Previous-stage and Latest-stage URI the cover declares actually retrieves | a live HEAD request for each docs.oasis-open.org URI in the Previous/Latest stage blocks | a definitive 404/410 from the published site (transport failures and non-404 errors stay INFO) | BLOCKER | md | - |

### symlinks

Self-referential symlinks materialize into unbounded recursion on deploy.

| # | Condition verified | Value pulled (observed) | Compared against | Severity | Applies | Requires |
|---|---|---|---|---|---|---|
| 142 | No symlink points at itself or an ancestor directory | each symlink's resolved target | must not equal or contain its own directory (deploys materialize symlinks into unbounded recursion) | BLOCKER | all | - |

### template

The OASIS template's required front-matter sections, in order, plus Conformance.

| # | Condition verified | Value pulled (observed) | Compared against | Severity | Applies | Requires |
|---|---|---|---|---|---|---|
| 143 | All required template front-matter sections are present | the markdown headings | the template's required set: This/Previous/Latest stage, Technical Committee, Chairs, Editors, Abstract | BLOCKER | md | - |
| 144 | Front-matter sections appear in template order | the order of found front-matter sections | the canonical template ordering | WARN | md | - |
| 145 | A Conformance section exists | the markdown headings | the TC Process requirement: every Standards Track Work Product carries conformance clauses | BLOCKER | md | - |

### template-css

The HTML must carry a stylesheet; the canonical CSS is the default expectation.

| # | Condition verified | Value pulled (observed) | Compared against | Severity | Applies | Requires |
|---|---|---|---|---|---|---|
| 146 | A non-canonical stylesheet keeps the template font family | the primary font-family declared by the HTML's own stylesheet | the template look: Liberation Sans / Arial / Helvetica | WARN | md | - |
| 147 | The HTML carries a stylesheet | the HTML's &lt;link rel=stylesheet&gt; and &lt;style&gt; elements | at least one styling source must be present | BLOCKER | md | - |

### title-oasis-prefix

A Work Product title should not begin with 'OASIS' unless Project Administration recommends it for a special case (Naming Directives v1.7 s7). BLOCKER on Standards Track, WARN on Non-Standards Track. The title is the cover `<h1>` that matches the HTML `<title>`; where the only difference is a trailing brand suffix on the `<title>`, the single `<h1>` is taken as the title. Where the stage prefix does not identify the track (`wd` sits on both), the finding and the observed evidence say which track was assumed.

| # | Condition verified | Value pulled (observed) | Compared against | Severity | Applies | Requires |
|---|---|---|---|---|---|---|
| 148 | The Work Product title (the &lt;h1&gt; identified by _h1_title_match_info's 'exact' or 'singular-related-fallback' classification) does not begin with the word 'OASIS' | the &lt;h1&gt; text identified by _h1_title_match_info: either the single &lt;h1&gt; exactly matching the rendered &lt;title&gt; text (the same match check_html's own D1 lint uses for its duplicate-title finding), or, when no exact match exists, the document's sole &lt;h1&gt; when it shares a prefix relationship with &lt;title&gt; (e.g. a trailing brand suffix on &lt;title&gt; alone), flagged lower-confidence in that case | naming-directives.txt s7: 'Preferably, a title should not begin with the name "OASIS" except on the recommendation of Project Administration for special cases.' Section 7's lead sentence track-scopes this to BLOCKER (Standards Track, must-observe) / WARN (Non-Standards Track, should-follow with an additional alternate-construction escape valve). | BLOCKER/WARN | all | - |

### title-version

The cover-page title must carry the package's own Version identifier, composed for a Standards Track Work Product as `<name> Version <number>` (Naming Directives 5.1 / Section 7).

| # | Condition verified | Value pulled (observed) | Compared against | Severity | Applies | Requires |
|---|---|---|---|---|---|---|
| 149 | The rendered cover-page title incorporates the package's own Version identifier | the resolved cover-page title text (HTML &lt;title&gt;/&lt;h1&gt; on the markdown track, the MsoTitle-styled or first non-empty non-logo cover paragraph on the DOCX-native track) | naming-directives.txt 5.1: 'A Version identifier must also be incorporated into a Work Product name/title' | BLOCKER | all | - |
| 150 | The Version cited in the title agrees with the package's own Version identifier | the numeric run of the rightmost 'Version &lt;n&gt;' token in the resolved title | the package's own Version identifier (the version directory segment, with a leading 'v' stripped per naming-directives.txt Section 4's [version-id] grammar) | BLOCKER | all | - |
| 151 | The title's Version token is composed as '&lt;name/identifier&gt; Version &lt;number&gt;' with no forbidden punctuation before it and only a sanctioned continuation after it | the characters immediately preceding and following the rightmost 'Version &lt;n&gt;' token in the resolved title, and the stage token's track classification | naming-directives.txt Section 7: MUST for Standards Track (csd/cs/os/errata) -&gt; BLOCKER; SHOULD for Non-Standards Track (cnd/cn) -&gt; WARN with the 'reasonable grounds for alternate constructions' exception; WARN also for any stage token outside the six Section-5.2-enumerated tokens (track unresolved, no corpus citation, never escalated to BLOCKER on an uncited classification) | BLOCKER/WARN | all | - |

### uri-alias

No unauthorized URI aliasing within a stage/revision package: META-refresh, byte-identical duplicate files, or a redirect/URL-shortening domain citing a canonical OASIS resource (Naming Directives v1.7 s6.5).

| # | Condition verified | Value pulled (observed) | Compared against | Severity | Applies | Requires |
|---|---|---|---|---|---|---|
| 152 | No live META-refresh element in any delivered HTML file | every &lt;meta&gt; tag in each .html/.htm/.xhtml file, HTML-tokenized (comments/&lt;script&gt;/&lt;style&gt;/&lt;pre&gt;/&lt;code&gt;/&lt;template&gt; excluded) | Naming Directives v1.7 s6.5(a): unauthorized URI aliasing via META-refresh elements is barred | BLOCKER | all | - |
| 153 | No stage-root delivery file or manifest-cited file (by exact package-relative path) shares byte-identical content with another package-relative path | sha256 of every regular file (symlinks resolved to their in-package target's bytes) in the stage/revision directory | Naming Directives v1.7 s6.5(b): preparing files with identical content under two different filenames within a published instance is barred | BLOCKER | all | - |
| 154 | An ancillary (non-delivery, non-manifest-cited) duplicate is flagged for review, not treated as a s6.5(b) aliasing risk | sha256 buckets whose members are all non-citable paths (LICENSE/NOTICE/schemas/test-fixtures/asset directories/etc.) | the package's own delivery-item paths and manifest.json authoritative/delivery-role paths | WARN | all | - |
| 155 | The markdown Previous-stage block cites no redirect/URL-shortening domain | every URL under the 'Previous Stage/Version' heading | the seed redirect-service domain list (tinyurl.com, bit.ly, goo.gl, ow.ly, t.co, is.gd, buff.ly, rebrand.ly, tiny.cc, cutt.ly, shorturl.at, rb.gy, purl.oclc.org) | BLOCKER | md | - |
| 156 | The DOCX-native rendered cover's This/Previous/Latest-version fields cite no redirect/URL-shortening domain | every URL (visible text or href) between the This/Previous/Latest-version labels on the rendered HTML cover | the seed redirect-service domain list | BLOCKER | docx | - |
| 157 | Plain-prose anchor text that names oasis-open.org does not link to a redirect/URL-shortening domain (markdown source) | the visible/anchor text of every [shown](target) (md) or &lt;a&gt;shown&lt;/a&gt; (html) construct whose shown text is not itself a URL (a shown-is-a-URL mismatch is the existing link-mismatch check's territory) | the seed redirect-service domain list, gated on the anchor text literally containing 'oasis-open.org' | BLOCKER | all | - |
| 158 | Plain-prose anchor text that names oasis-open.org does not link to a redirect/URL-shortening domain (HTML render) | the visible/anchor text of every [shown](target) (md) or &lt;a&gt;shown&lt;/a&gt; (html) construct whose shown text is not itself a URL (a shown-is-a-URL mismatch is the existing link-mismatch check's territory) | the seed redirect-service domain list, gated on the anchor text literally containing 'oasis-open.org' | BLOCKER | all | - |
| 159 | A bare URL's enclosing sentence that names oasis-open.org does not point at a redirect/URL-shortening domain (markdown source) | the sentence-bounded prose window (nearest sentence terminator or paragraph break either side) around every bare URL not part of a link construct | the seed redirect-service domain list, gated on the sentence window literally containing 'oasis-open.org' | BLOCKER | all | - |
| 160 | A bare URL's enclosing sentence that names oasis-open.org does not point at a redirect/URL-shortening domain (HTML render) | the sentence-bounded prose window (nearest sentence terminator or paragraph break either side) around every bare URL not part of a link construct | the seed redirect-service domain list, gated on the sentence window literally containing 'oasis-open.org' | BLOCKER | all | - |

### uri-chars

No underscore may appear in a document (cover-page) URI (Naming Directives v1.7 s3).

| # | Condition verified | Value pulled (observed) | Compared against | Severity | Applies | Requires |
|---|---|---|---|---|---|---|
| 161 | No underscore appears in a This/Latest-stage document URI | the percent-decoded path of each This-stage and Latest-stage cover URI | Naming Directives v1.7 s3: '_' is barred from any filename or directory name used in a document URI | BLOCKER | md | - |

### version-naming

The version directory and delivery filenames must agree on one vN.N(.N) version.

| # | Condition verified | Value pulled (observed) | Compared against | Severity | Applies | Requires |
|---|---|---|---|---|---|---|
| 162 | Version directory matches the vN.N(.N) convention | the version directory name from the package path | the Naming Directives version-segment pattern vN.N(.N), e.g. v1.0, v2.0.1 | BLOCKER | all | - |
| 163 | Version embedded in the delivery filename agrees with the version directory | the version segment embedded in the delivery filename stem | the version directory the package publishes under | BLOCKER | all | - |
| 164 | Delivery filename embeds the version segment | the delivery filename stem | the Naming Directives filename shape &lt;base&gt;-&lt;version&gt;-&lt;stage&gt; | WARN | all | - |

### vml-fallback

VML-only images in Word HTML renders are invisible in every modern browser.

| # | Condition verified | Value pulled (observed) | Compared against | Severity | Applies | Requires |
|---|---|---|---|---|---|---|
| 165 | Every VML image has an &lt;![if !vml]&gt; img fallback | the counts of v:imagedata elements and vml-fallback img tags | fallback count must cover VML count (the invisible-cover-logo class) | BLOCKER | all | - |

### xml-namespace

Every namespace a packaged .xsd/.wsdl/.rng declares as its own must be a docs.oasis-open.org/[tc-shortname]/ns/xxxx URI (consistent scheme) or an allowlisted urn:.

| # | Condition verified | Value pulled (observed) | Compared against | Severity | Applies | Requires |
|---|---|---|---|---|---|---|
| 166 | An http(s) namespace's tail matches the docs.oasis-open.org/[tc-shortname]/ns/xxxx pattern | targetNamespace on the root of each packaged .xsd/.wsdl (incl. wsdl:types-embedded schemas), and the ns attribute on the root grammar/element of each .rng | Naming Directives s8 pattern http(s)://docs.oasis-open.org/[tc-shortname]/ns/xxxx, xxxx restricted to the s3 sixty-four-character set plus internal '/', terminating in '/', '#', or alphanumeric; BLOCKER when the tc-shortname has no pattern-grandfather allowlist entry | BLOCKER | all | - |
| 167 | A pattern-mismatched namespace's tc-shortname is a confirmed-approved pre-2012 pattern grandfather | the same pattern-mismatched namespace URI, matched against the pattern-grandfather allowlist | Naming Directives v1.2 s9: pre-2012 practice 'may be grandfathered, if approved by Project Administration': WARN when listed but approval is not machine-confirmable at check time | WARN | all | - |
| 168 | The same namespace tail is declared under one scheme only, package-wide | every http(s) namespace URI declared by any packaged .xsd/.wsdl(+embedded)/.rng in the package, grouped by scheme-stripped tail | Naming Directives s8: 'While either "http" or "https" may be used ... they are not interchangeable. One or the other must be used consistently.' | BLOCKER | all | - |
| 169 | A urn:-scheme declared namespace's TC is on the URN-grandfather allowlist | the urn:-scheme namespace URI and its owning tc-shortname | Naming Directives s8: URN-based namespaces 'must not be declared otherwise', permitted only for TCs that already used the feature (or Maintenance Activity TCs), approved by Project Administration | BLOCKER | all | - |
| 170 | A RELAX NG grammar declares only one namespace, on its root grammar/element node | every ns attribute on non-root nodes of a .rng file, compared to the root node's ns | this check only validates the root-level self-declared namespace; a differing non-root ns is flagged for manual review rather than silently dropped | WARN | all | - |

---

Generated from `oasis_pub_check.py` by `render_checks_md.py`. The inventory is
asserted from the code: `python3 oasis_pub_check.py --list-checks` fails if the
registry and the implementation disagree in either direction.

**The documentation set:** [Repository overview](../README.md) · [TC guide](../PUBLICATION-QUALITY.md) · [The acceptance criteria tool](README.md) · [Worked example](../examples/eox-core-v1.0-csd01/README.md) · [The pipeline, command by command](../TRANSFORMS.md) · [Architecture diagrams](../assets/architecture/README.md)
