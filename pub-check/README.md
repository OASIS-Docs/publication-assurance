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

# oasis-pub-check: the OASIS publication acceptance criteria in executable form

**Author: Michael Coletta, Technical Advisor, OASIS Open**

![oasis-pub-check: the acceptance criteria](../assets/gate.png?v=170)

`oasis_pub_check.py` is the executable form of the publication acceptance
criteria: the TC-side version of the checks OASIS TC Administration
applies to a submitted work-product package before it goes to
`docs.oasis-open.org`. Blockers are cheaper to fix before the vote than
after publication.

TC Administration runs the same gate on every submission at intake. Both
sides run the same code, so a green run on your side predicts a green run at
intake.

Characteristics:

- Single file, Python 3.10+, standard library only. Nothing to install.
- No configuration. Every expectation is derived from the package itself:
  its own front matter, its own CSS, its own schema `$id`s, its own publish
  path.
- 170 individual checks across 58 check classes. `--list-checks` asserts
  that inventory against the code, and every count advertised anywhere in
  this repository comes from it.
- It combines the intake acceptance criteria with the publication
  pipeline's lint registry (D1-D7 and the PDF assertions A1/A2), checked
  against a year of submissions as received.

Three companion documents:

- [CHECKS.md](CHECKS.md): the per-condition catalog, one row per check with
  the value the tool pulls and what it compares that value against.
  Generated from the code's own condition registry by
  [render_checks_md.py](render_checks_md.py).
- [../PUBLICATION-QUALITY.md](../PUBLICATION-QUALITY.md): the TC-facing
  guide to the validation and audit layers.
- [../examples/eox-core-v1.0-csd01/](../examples/eox-core-v1.0-csd01/):
  the Validation Report from a publication.

## Usage

```bash
# against a stage directory
python3 oasis_pub_check.py openeox/eox-core/v1.0/csd01/

# against a submission zip
python3 oasis_pub_check.py eox-core-1.0-csd-01-20260713-rc3.zip

# machine-readable
python3 oasis_pub_check.py <target> --json

# the check inventory, asserted from the code itself (source of the advertised numbers)
python3 oasis_pub_check.py --list-checks

# write the release manifests: manifest.json (machine) and the
# <stem>-manifest.txt Work Product Manifest File (staff record)
python3 oasis_pub_check.py <target> --emit-manifest
```

Exit 0 means publishable (warnings allowed). Exit 1 means blockers. Exit 2
means the target could not be read: a wrong path, or a `.zip` that would not
open.

## Where the checks come from

Each check comes from written OASIS policy (the TC Process, the Naming
Directives, the RFC 2119/8174 key-word rules) or from a correction round in
OASIS publication work across CSAF, KMIP, PKCS#11,
OpenEoX, NIEM, Akoma Ntoso and LegalDocML, DMLex, UBL, Electronic Court
Filing, STIX, OSLC, Virtio, DPS, ACAL, and OpenDocument, authored in
Markdown, Word, ODT, DocBook/XML, and LaTeX. The correction rounds behind
the checks include:

- an editor placeholder that went live and stayed for years
- a mixed-case citation that 404ed on the case-sensitive host
- a PDF rendered from an older draft than the HTML beside it
- front matter citing files that were never published
- a retired stage token in a published path
- dangling internal anchors that two human review passes had missed
- a self-referential symlink a deploy materialized into 41 nested directories

The template and TC Process requirements (the Conformance section, the RFC
2119/8174 key-word references, the Naming Directives) are enforced as
checks in the same set.

Calibration:

- a regression corpus of 12 archived CSAF and CSAF-CVRF packages as
  received, across multiple authoring tracks
- one known-bad release candidate whose blocker set matches the one TC
  Administration had established by hand
- a retrospective over a year of intake, as received, which surfaced live
  defects on docs.oasis-open.org; those became checks too

New failure modes from later correction rounds become new acceptance
criteria. The catalog and the advertised counts regenerate from the code, so
the criteria in force are the ones the tool runs.

## The checks

Every check class the tool runs, with the number of individual conditions in it
and the severity it can reach. The full per-condition catalog, with the value
pulled and the value compared against, is [CHECKS.md](CHECKS.md).

<!-- BEGIN generated class table: render_checks_md.py -->

| Check | Conditions | Severity | What it catches |
|---|---|---|---|
| artifact-naming | 1 | WARN | Non-document-identifier artifacts (schemas, images, WSDLs, codelists) should keep stable filenames across releases, not embed a stage/revision token. |
| asset-refs | 1 | BLOCKER | Relative files the HTML references must be included in the package. |
| authors | 4 | BLOCKER/WARN | A Technical Report/Technical Report Draft must name one or more Authors on the cover page, distinct from a Committee Note's Editors listing. |
| boilerplate-dup | 1 | WARN | The template's comments/status boilerplate paragraph appears exactly once. |
| case | 3 | BLOCKER/WARN | The publication host is case-sensitive; canonical paths are lowercase. |
| comment-resolution-log | 2 | BLOCKER/WARN | A comment-resolution log accompanying a CSD or CND public review must carry the exact basename the Naming Directives prescribe (BLOCKER if it is misnamed). Where the package itself shows the review concluded and no log-named file is present, the absence is flagged for confirmation (WARN). A near-miss is matched across hyphen and underscore word-joiners only, so a file that merely shares a word or two is not read as a misnamed log. |
| conformance-structure | 9 | BLOCKER/WARN | Standards Track Conformance section structure: the section sits at top level rather than inside an Annex or subsection, each profile scope carries individually and uniquely numbered clauses, and from CS to OS the clause-number set is preserved exactly, with wording-only changes flagged for manual review. |
| content-labels | 1 | WARN | An Examples or Sample heading should carry an explicit non-normative or informative content-type label (WARN). Appendix and Annex headings get the same structural test, recorded as an advisory note that does not score. |
| cover-hr | 1 | WARN | A horizontal rule above the title opens the OASIS-rendered PDF with a blank page. |
| date-sync | 2 | BLOCKER/WARN | The markdown, HTML, and copyright dates must describe the same revision. |
| dead-lists | 3 | BLOCKER/WARN | Mail addresses at lists.oasis-open.org fail silently; comments go through Higher Logic. |
| double-slash | 1 | BLOCKER | A double slash inside a relative path 404s on the CDN. |
| extension-conformance | 1 | WARN | Principal and Multi-Part named-part filename extensions should match a common OASIS publication rendering format, not an invented or proprietary token. |
| extension-count | 4 | BLOCKER/WARN | A delivery item must carry exactly one file extension after its document-identifier stem: BLOCKER, relaxed to WARN at wd stage (Naming Directives v1.7 s4/s9). Compound archive extensions (`tar.gz`, `tar.bz2`, `tar.xz`) count as one. Every other file in the package gets the same double-extension and missing-extension test as a non-blocking advisory. |
| fence-collapse | 1 | BLOCKER | An opening code fence with trailing text collapses the whole block under pandoc. |
| filenames | 6 | BLOCKER/WARN | Delivery items are named for the published stage, one basename, all formats present. |
| front-matter | 12 | BLOCKER/WARN | The This/Latest stage URL blocks must match the package's actual publish path. |
| generator | 1 | BLOCKER | DOCX-native renders must come from Microsoft Word, matching the TC's precedent. |
| html-anchors | 2 | BLOCKER/WARN | Every internal fragment link must resolve to an anchor in the document. |
| html-residue | 3 | BLOCKER | Pipeline residue in the HTML: duplicate title H1, stale pandoc header, CI paths. |
| html-title | 2 | BLOCKER/WARN | The HTML title element must be an actual document title with no working residue. |
| image-policy | 10 | BLOCKER/WARN | Images must be self-contained, inert, and within the pipeline's size caps. |
| junk-files | 2 | BLOCKER | OS and editor junk must not be in the package. |
| link-mismatch | 2 | BLOCKER | A visible URL and its link target must agree. |
| logo | 1 | WARN | The cover logo should be the canonical OASIS template logo. |
| manifest | 3 | BLOCKER | A packaged manifest.json must verify against the files on disk. |
| md-links | 2 | BLOCKER/WARN | Markdown link forms that render wrong under pandoc autolinking. |
| member-uri | 1 | BLOCKER | No OASIS member-only (Kavi) URI may be cited in a public work product (Naming Directives v1.7 s6.6). |
| multi-part-naming | 8 | BLOCKER | Multi-Part Work Product filenames must share one work-product abbreviation and version id (AC-NAMING-19) and, in a multi-part package, carry a well-formed, contiguously numbered `-partN-name` segment (AC-NAMING-20; Naming Directives v1.7 s4/s6.1). Scoped to Standards Track CSD/CS/OS and Non-Standards Track CND/CN stage directories. |
| name-chars | 4 | BLOCKER | Every filename and directory name must stay within the sixty-four permitted characters. UNDERSCORE is a BLOCKER in an identifying (document-URI) name and a WARN elsewhere. An empty identifying name is a BLOCKER. |
| normdef-refs | 2 | BLOCKER/WARN | Every packaged normative schema/grammar/code file (Standards Track) must be referenced from the Work Product (TC Process 2.2.5). |
| ns-segment | 2 | BLOCKER/WARN | This/Latest-stage cover URIs must not reuse the reserved /ns/ path segment (namespace identifiers only); Previous-stage hits are WARN (inherited, immutable citation). |
| odt-integrity | 6 | BLOCKER | The ODT source must be a valid, macro-free OpenDocument container. |
| package-refs | 1 | BLOCKER | Files the document cites under its own stage path must be included in the package. |
| pdf-cover | 2 | BLOCKER | The rendered PDF cover must carry the title exactly once and no CI paths. |
| pdf-fonts | 2 | WARN | PDF embedded fonts are compared against the package's own CSS as typography authority. |
| pdf-sync | 5 | BLOCKER/WARN | The PDF must be readable and rendered from the same revision as the rest of the package. |
| previous-stage | 2 | BLOCKER | Second and later stages must cite the previous stage's URLs. |
| public-review-metadata | 3 | BLOCKER/WARN | Post-publication audit: a csd/cnd stage directory that underwent a TC public review must carry the [WP-abbrev]-[version-id]-[stage-abbrev][revisionNumber]-public-review-metadata.html companion file Project Administration is obligated to publish alongside it (Naming Directives v1.7 s5.2 / TC Handbook Naming). |
| ref-rfc | 2 | WARN | An [RFCnnnn] references entry's label, body text, and URL must cite the same RFC number. |
| references-split | 2 | WARN | On a Standards Track work product, Normative and Informative References should be separately labeled, with no reference ID listed under both (handbook-WPQualityChecklist.txt, WARN). |
| residue | 4 | BLOCKER/WARN | Editor placeholders (TODO, tbd, 'Will be filled in') must not be present. |
| revision-collision | 1 | WARN | A new submission must not collide with a stage already live for the version. |
| rfc-keywords | 2 | BLOCKER/WARN | Normative key words require the RFC 2119 (and 8174) citations. |
| schema-id | 4 | BLOCKER/WARN | Every JSON schema's $id must agree with where the file actually publishes. |
| stage-name | 3 | BLOCKER | The stage token must be a current, correctly numbered stage per the Naming Directives. |
| stage-token | 3 | BLOCKER/WARN | On a second or later stage, the Previous-stage cover URI should carry the document's own csd or cnd stage token; a retired or mismatched token is a WARN, with a caveat for pre-v1.7 legacy paths. A Latest-stage cover URI filename must carry no stage-abbreviation or revision token (BLOCKER). |
| stage-uri-live | 1 | BLOCKER | The Previous-stage and Latest-stage URIs on the cover name files that are not in the package, so every other check can see only their shape. This class fetches them. A 404 or 410 is a BLOCKER: the cover cites a document that was never published at that address, usually because the template hardcodes the extension while templating the stage name, so a stage that went markdown-native is still cited as `.docx`. Transport failures, 5xx responses and bot challenges are recorded as INFO. `PUB_CHECK_OFFLINE` turns the class off. |
| symlinks | 1 | BLOCKER | Self-referential symlinks materialize into unbounded recursion on deploy. |
| template | 3 | BLOCKER/WARN | The OASIS template's required front-matter sections, in order, plus Conformance. |
| template-css | 2 | BLOCKER/WARN | The HTML must carry a stylesheet; the canonical CSS is the default expectation. |
| title-oasis-prefix | 1 | BLOCKER/WARN | A Work Product title should not begin with 'OASIS' unless Project Administration recommends it for a special case (Naming Directives v1.7 s7). BLOCKER on Standards Track, WARN on Non-Standards Track. The title is the cover `<h1>` that matches the HTML `<title>`; where the only difference is a trailing brand suffix on the `<title>`, the single `<h1>` is taken as the title. Where the stage prefix does not identify the track (`wd` sits on both), the finding and the observed evidence say which track was assumed. |
| title-version | 3 | BLOCKER/WARN | The cover-page title must carry the package's own Version identifier, composed for a Standards Track Work Product as `<name> Version <number>` (Naming Directives 5.1 / Section 7). |
| uri-alias | 9 | BLOCKER/WARN | No unauthorized URI aliasing within a stage/revision package: META-refresh, byte-identical duplicate files, or a redirect/URL-shortening domain citing a canonical OASIS resource (Naming Directives v1.7 s6.5). |
| uri-chars | 1 | BLOCKER | No underscore may appear in a document (cover-page) URI (Naming Directives v1.7 s3). |
| version-naming | 3 | BLOCKER/WARN | The version directory and delivery filenames must agree on one vN.N(.N) version. |
| vml-fallback | 1 | BLOCKER | VML-only images in Word HTML renders are invisible in every modern browser. |
| xml-namespace | 5 | BLOCKER/WARN | Every namespace a packaged .xsd/.wsdl/.rng declares as its own must be a docs.oasis-open.org/[tc-shortname]/ns/xxxx URI (consistent scheme) or an allowlisted urn:. |

<!-- END generated class table -->

Residue, key-word and link checks ignore fenced code blocks and `<pre>/<code>`
content, so schemas and examples containing `tbd` or bare URLs are not
flagged. That matters most for specifications carrying large embedded code
samples.

## The manifest contract

Every OASIS publication now includes two manifest artifacts, generated by the
same command on either side of the gate (`--emit-manifest`):

- `manifest.json`: the machine contract below, verified mechanically at
  intake.
- `<stem>-manifest.txt`: the Work Product Manifest File, the
  human-readable staff record published beside the release: bibliographic
  block, ZIP archive listing, and SHA-256 digests. The
  [OpenDocument releases](https://docs.oasis-open.org/office/OpenDocument/v1.4/csd01/OpenDocument-v1.4-csd01-manifest.txt)
  carry the precedent.

![The verification chain](../assets/chain.png?v=170)

If the package includes a `manifest.json` conforming to
[`manifest-schema.json`](manifest-schema.json), the intake side can verify
the whole package mechanically: per-file sha256, the source commit the
artifacts were built from, and the tool versions that built them. Emit it
from your own toolchain, or with `--emit-manifest`. Minimal shape:

```json
{
  "version": "v1.0",
  "stage": "csd01",
  "source": { "repo": "oasis-tcs/openeox", "commit": "<sha>", "tag": "<release tag>" },
  "tools": { "pandoc": "pandoc 3.8.2.1", "typst": "typst 0.15.0" },
  "items": [
    { "path": "eox-core-v1.0-csd01.md", "role": "authoritative", "sha256": "...", "bytes": 70555 }
  ]
}
```

Roles: `authoritative`, `delivery`, `schema`, `example`, `other`.

## CI

`.github/workflows/pub-check.yml` in this repository shows the whole CI
story: checkout, Python, `apt-get install poppler-utils` for the optional
PDF cross-check, then one command. There is nothing else in it. A makefile
target works just as well:

```make
.PHONY: pub-check
pub-check:
	python3 oasis_pub_check.py ../share/  # or your stage dir
```

## Scope and track detection

The gate measures the output, which is the same contract for every TC:
conformant HTML and PDF at the canonical URLs, with the authoritative source
alongside. The full output suite runs on every package, whatever it was
authored in. That is the HTML checks (title, anchors, residue, image policy,
asset refs, rendered front-matter blocks), the PDF checks (source sync, cover
assertions, fonts), and the package checks (naming, versioning, stage,
collision, hygiene, symlinks, schemas, manifest). Source-format checks are
add-ons applied to whatever the package carries:

- Markdown source present: the markdown add-ons (front-matter cross-check,
  autolink trap, fence-collapse, template sections, correction classes).
- Word source present, no markdown (KMIP, PKCS#11 style): the Word
  render-fidelity add-ons (Microsoft Word generator, VML image fallbacks),
  with the front-matter blocks parsed from the rendered HTML cover. Dangling
  internal anchors report as warnings here: they are source-DOCX artifacts
  whose fix path is the TC's next revision.
- ODT source present, no markdown or Word: the `.odt` is the
  authoritative source and satisfies the source-travels contract (the
  OpenDocument TC publishes from the format it defines:
  [OpenDocument v1.4](https://docs.oasis-open.org/office/OpenDocument/v1.4/)).
  The full output and package suites run, the cover is parsed from the
  rendered HTML, and the ODT source-integrity checks verify the container
  itself: a valid OpenDocument archive, the declared mimetype, a parseable
  document body, and no embedded macros. Deeper render-fidelity add-ons
  grow the same way the existing tracks did, calibrated against the
  published corpus.
- None of the above (DocBook/XML, LaTeX, and other TC-rendered formats):
  the full output and package suites still run; a warning asks for the
  authoritative source to travel with the renderings.

Other authoring formats exist in the published corpus: DocBook/XML (UBL and
Electronic Court Filing, where the XML is often the authoritative artifact),
LaTeX (Virtio), and others. Packages in those formats get the
format-agnostic checks: stage naming, version-naming, revision collision,
case, hygiene, symlinks, dead-lists, and the link and packaging checks.
Add-ons of their own are planned, calibrated against the published corpus
the same way the first ones were.

The gate does not ask a TC to repackage or re-render into another track's
format. Render class is judged against the TC's own publication precedent.

---

**The documentation set:** [Repository overview](../README.md) · [TC guide](../PUBLICATION-QUALITY.md) · [The criteria catalog](CHECKS.md) · [Worked example](../examples/eox-core-v1.0-csd01/README.md) · [The pipeline, command by command](../TRANSFORMS.md) · [Architecture diagrams](../assets/architecture/README.md)
