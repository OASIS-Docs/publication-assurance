<!--
Copyright (c) OASIS Open 2026. All Rights Reserved.

This document may be copied, published, and distributed to others without
restriction, provided it is reproduced verbatim and this notice is retained.
Author: Michael Coletta, Technical Advisor to OASIS Open.
-->

# Changelog

Every release of the acceptance criteria gets an entry here, newest first,
referencing the GitHub issue(s) that drove it and the exact criteria that
changed, so the audit trail between versions is readable in one place.
The advertised check counts are asserted from the code by `--list-checks`,
never hand-counted.

Versioning follows the publisher-toolkit convention:

- **MAJOR**: a breaking contract change (exit-code semantics, `--json`
  shape, retired nide rule ids).
- **MINOR**: a new check, check class, or nide rule (the gate got stricter).
- **PATCH**: a fix inside an existing check, or documentation/diagram
  corrections (no new criteria).

Each version is anchored by a git tag on this repository.

## v1.3.0 - 2026-09-05

Prepared for handing the criteria to the TCs. No check was added or removed
and no finding changes severity. It is a MINOR rather than a PATCH for two
reasons: the `applies` field in `--json` and in the catalog now says `all`
where it said `both`, and the rendering pipeline stopped putting one TC's
title on another TC's PDF.

Contract:

- **`applies: "both"` is now `applies: "all"`.** The vocabulary dated from a
  two-track world, markdown and DOCX, and the tool has had three source
  formats since ODT landed. "Both" was wrong on its face in a column whose
  other values are `md`, `docx` and `odt`. The `--json` keys are unchanged
  and the exit-code contract is unchanged; a consumer that branches on the
  string `"both"` must read `"all"` instead. TC Administration's own report
  renderer branches only on `md`, `docx` and `odt`, so it is unaffected.

Defects in the shipped documentation:

- **`CHECKS.md` was rendering a third of a paragraph at heading size.** The
  generator escaped angle brackets in the table cells but not in the
  class-description paragraphs, and the `title-oasis-prefix` description
  contains `<h1>`. GitHub parses that as an opening heading tag, so
  everything after it on the page rendered at 32 point. Tags GitHub does not
  recognise, `<spec>` and `<name>` among them, were deleted from the page
  instead, silently. `AUTHORITIES.md` carried the same defect in a heading
  and inside a verbatim policy quote. Both generators now escape angle
  brackets in prose, leaving code spans alone, and
  `tests/test_markdown_renders.py` fails on any angle-bracketed text that
  reaches a shipped document unescaped.

- **The catalog shipped dead links.** The dual-link check was described as
  "No dual `[url](url)` links", which markdown renders as a link to a
  relative path named `url`. Two per row, in the rows most likely to be read
  by somebody whose package just failed that check. The registry text now
  puts the illustrations in backticks, and the same test file asserts that
  every relative link in every shipped document resolves to a file.

- **The regression corpus was advertised as 13 packages.** `examples/`
  carries 12 stage packages. `tests/test_advertised_counts.py` now counts
  them and fails on any document that says otherwise, the same way it
  already pins the condition and class counts.

- **The worked example was described with the wrong figures.** The TC guide
  said the eox-core CSD01 validation report showed zero blockers "across all
  92 conditions", with 9 warnings and 3 informational notes. The report
  itself records 169 conditions across 57 classes, 12 warnings and 9
  informational notes. The count claim is gone (the report is dated evidence
  and its inventory is not today's), and the warning and informational
  figures now match the report.

- **A count claim can hide from the count test by being wrapped.** That 92
  sat in `PUBLICATION-QUALITY.md` through a green suite because the line
  broke between "92" and "conditions" and the patterns were single-line. The
  claim patterns now match against whitespace-collapsed text.

- **The TC guide said Layer 1 "never touches the live site".** Four checks
  do: `revision-collision`, `stage-uri-live`, `public-review-metadata`, and
  the previous-stage resolution inside `conformance-structure`. The guide now
  says which, and says that `PUB_CHECK_OFFLINE=1` turns those four off. It
  also no longer implies the tool writes nothing, since `--emit-manifest`
  does.

Defects found while checking the documentation against the code:

- **The same package did not produce the same report twice.** Nine finding
  loops iterated a `set()` directly, so under Python's per-process hash
  randomisation the findings came out in a different order between runs of
  identical code on identical input: six runs against one corpus package
  produced two different reports. TC Administration files these as the record
  of a publication, and a TC diffing two runs saw churn that meant nothing.
  All nine are sorted now, `tests/test_output_is_deterministic.py` runs three
  corpus packages six times each and requires one distinct output, and the
  finding sets on four corpus packages are byte-identical to the previous
  release once sorted.

Defects the fact-check found in the pipeline and its documentation:

- **Every PDF this repository's pipeline rendered carried another TC's title.**
  `PdfRenderer.build_command` passed the literal string `Common Security
  Advisory Framework Version 2.1` as `--header-center`, so that ran across the
  top of every page of every PDF, for every TC, and `--footer-center` carried a
  hardcoded `2025`. Both are now read from the document being rendered: the
  `<title>` element (falling back to the first heading, then to an empty
  header), and the copyright year in the document's own front matter.
  `tests/test_pdf_command.py` pins them, and CI now installs `beautifulsoup4`
  so those tests run rather than skip. Nothing in this repository had ever
  exercised the pipeline, which is why nothing caught it.

- **`TRANSFORMS.md` printed two commands that were not the ones the pipeline
  runs.** The pandoc invocation, labelled "the exact pandoc invocation the
  pipeline uses", carried `+hard_line_breaks` and `--toc` (which the pipeline
  dropped) and lacked `-implicit_figures` and `--no-highlight` (which it
  added). A TC copying it got a `<br/>` per source line, alt text rendered as
  figure captions, syntax-highlighted code, and a second table of contents. The
  wkhtmltopdf vector omitted `--load-error-handling ignore` and
  `--load-media-error-handling ignore`, so the documented command dies on an
  unreachable image where the pipeline continues. Both now match the code, and
  a test asserts the documented flags against the vector the code builds.

- **`TRANSFORMS.md` named a file that contains no code.** The nine
  post-processing steps live in `HtmlConverter._post_process_html` in
  `.github/src/pipeline/html_converter.py`; the document sent readers to
  `step_1_markdown_to_html_converter_V3_0.py`, a forty-line CLI shim with no
  function definitions in it. It also called six workflows three.

- **The catalog's Requires column under-declared the network.** Only
  `revision-collision` carried `requires="network"`, while `stage-uri-live` and
  the three `public-review-metadata` conditions also issue live HTTP requests.
  Offline, those four are skipped, and the catalog implied they had been
  evaluated. They now declare it, so a validation report NAs them with the
  reason instead.

- **Exit code 2 was documented nowhere.** The tool returns 2 when the target
  cannot be read, `tests/test_cli_smoke.py` pins it, and the composite action
  re-raises it, while the README, the tool README and `action.yml` all
  described a world with only 0 and 1. A consumer whose `target:` path was
  wrong read the failure as blockers. All three now say what 2 means.

- **`--emit-manifest` writes two files, and `--help` named one.** The README
  said "the release manifest", singular. Both now name `manifest.json` and the
  `<stem>-manifest.txt` Work Product Manifest File.

- **The per-area totals were printed, never asserted.** The generator asserts
  that the six areas are a partition of the registry and sum to its total, and
  the TC guide claimed on that basis that its 39/44/17/26/23/21 could not go
  wrong. Moving one class between areas would have left every gate green and
  the table silently wrong. `tests/test_advertised_counts.py` now reads the six
  figures out of the guide and compares them with the registry; the guide's
  claim is narrowed to what the generator actually asserts.

- **"25 pages, snapshotted and hashed" was true and unverifiable.** The corpus
  holds 25 snapshotted source pages, 19 of them cited, and neither the corpus
  nor its `MANIFEST.json` nor the crosswalk ships in this repository, so
  `AUTHORITIES.md` pointed a TC at three paths that do not exist here. The
  preamble now says what the corpus is, that TC Administration holds it, and
  that `authorities.yaml` beside the file is the machine-readable half that
  does ship.

- **"13 blockers it reproduces exactly" cannot be reproduced from this
  repository.** The release candidate is not in `examples/` and no test pins
  the count. The claim is now stated as what it is: a known-bad release
  candidate whose blocker set TC Administration had established by hand. The
  same applies to the "fires exactly 28 times" calibration note, which is gone
  from the class table.

- **Smaller corrections.** The README's layout block omitted `authorities.yaml`,
  `render_summary.py`, `consumer-workflow-matrix.yml` and the `make-manifest`
  workflow, and described `assets/` as PNG when the SVG sources are tracked and
  gated. The TC guide linked "a single Python file" to a directory. The README
  snippet and the drop-in consumer workflow both handed out
  `actions/checkout@v4` while the action's own documentation and every workflow
  here use `v5`. The tool README described a 35-row table as the class-level
  summary of 58 classes.

Register:

- Class descriptions in `CHECKS.md` described the implementation to a reader
  who does not have it open: a helper shared with another check, an
  extraction that is "percent-decode-aware", a fallback taken "rather than
  skipping a real violation". Ten of them are rewritten to say what the check
  requires of a package and what happens when it is not met.

- Passages across the README, the TC guide and the tool README that defended
  a choice nobody had questioned, or narrated the author's own diligence, are
  cut or restated as plain description. The layout listing in the README was
  four test files behind.

## v1.2.0 - 2026-09-04

A minor release: one new check class, so the gate got stricter.
**169 -> 170 checks, 57 -> 58 classes.** The exit-code gate contract, the
`--json` shape and every existing rule id are unchanged, so a consumer
pinned to v1.1.x sees no behaviour change other than the new condition.

The release also corrects the drift in this repository's own documentation
and puts a CI gate in front of it.

Criteria:

- **`stage-uri-live` (BLOCKER/INFO, markdown track).** `check_front_matter`
  validated the *shape* of the Previous-stage and Latest-stage URI blocks
  and validated This-stage URIs against the package's own file list.
  Nothing confirmed a Previous- or Latest-stage URI actually resolves.
  Those two blocks name files that are not in the package, so shape is all
  a local check can see, and a citation pointing at a file that was never
  published passed every gate silently. Found on OData Vocabularies v4.0
  csd03, published and under public review: the cover cited csd02 as
  `.docx` (404, because csd02 went markdown-native) and a version-root
  `.docx` that resolved to the December 2016 csprd01 document. The TC's
  template hardcodes the extension while templating the stage name, so the
  defect recurs at every stage. Only a definitive 404 or 410 raises a
  BLOCKER; timeouts, DNS failures, 5xx and bot-challenge responses are
  reported as INFO so a network fault cannot manufacture a publication
  defect, and the whole check is a silent no-op under `PUB_CHECK_OFFLINE`.
  The Previous-stage block had been excluded deliberately, on the grounds
  that it cites an immutable prior artifact the TC cannot rename. That
  reasoning holds for renames; it does not hold for a citation pointing at
  a file that does not exist.

- **`stage-uri-live` shipped without a regression fixture.** v1.1.8
  established one fixture per fixed defect; the check added on 31 August had
  none, so a release promoting it to a MINOR version would have advertised an
  untested gate. `tests/test_stage_uri_live.py` adds eight, stubbing
  `urlopen` to pin the distinction the class rests on: 404 and 410 block, a
  transport failure and a 5xx stay INFO, `PUB_CHECK_OFFLINE` short-circuits
  before the first request, and an off-site URI is never probed. Each was
  demonstrated failing against a deliberate mutation of the check before it
  was accepted. The suite goes from 17 tests to 25.

Generated artifacts and their CI gate:

- **`render_checks_md.py` had been failing since 31 August.** The
  `stage-uri-live` commit added a check class without a line in
  `CLASS_DESCRIPTIONS`, which the generator treats as a hard error by
  design. Nothing in CI ran the generator, so `CHECKS.md` simply stayed at
  169 conditions across 57 classes for twelve days while the tool ran 170
  across 58. The description is now written and the catalog regenerated.
- **CI now regenerates `CHECKS.md` and diffs it, and the suite asserts every
  advertised count.** `--list-checks` proved the condition registry matched
  the code, so the registry never drifted. Nothing proved the generated
  documentation matched the registry, and that is where it drifted. An
  unregenerated catalog is now a red run.
  `tests/test_advertised_counts.py` closes the rest: it reads the committed
  documentation, the diagram sources and the README badge, and fails on any
  count that disagrees with the registry. Run against the previous commit it
  fails on seven of the eight artifacts it covers, which is the whole defect
  this release fixes. The diagrams are deliberately checked by reading them
  rather than by regenerating them: `assets/build.py` is a gitignored local
  authoring helper, so a CI step that ran it could only ever fail. `CHANGELOG.md`
  and `examples/` are excluded, because a historical entry and a dated
  validation report are supposed to keep the counts they were written with.
- **The six advertised areas are a machine-checked partition.**
  `render_checks_md.py` carries the class-to-area map, asserts every class
  is assigned exactly once and that the areas sum to the registry total,
  and prints the per-area figures. A new class fails the generator until it
  is placed, the same way it fails until it has a description.
- **Diagrams regenerated.** `assets/build.py` already derives the advertised
  counts from `--list-checks`, so the eight SVGs and their PNGs pick up
  170/58 on rebuild. The image cache-busting query strings had fallen out of
  step with each other (`?v=169` in the README, `?v=164` in the TC guide,
  `?v=98` in the tool README), which would have served the old
  diagrams from cache to readers of the TC guide and the tool README. All
  three are now `?v=170`.

Documentation corrections:

- **The TC-facing area table never matched a released count.** The six
  per-area figures in `PUBLICATION-QUALITY.md` summed to 98, which predates
  v1.0.0's 165, while the tool now runs 170. They read 39 / 44 / 17 / 26 /
  23 / 21, and the area descriptions name what the areas actually contain.
- **`AUTHORITIES.md` stated the wrong totals** (issue #2). Its preamble
  said 165 conditions with 93 grounded and 72 not, which was the v1.0.0
  registry, and it kept saying so through the v1.1.1 crosswalk extension.
  Measured against the registry: 170 conditions, of which **96 are grounded
  in written policy**, appearing as 93 catalog entries because three check
  signatures each cover two conditions (the markdown-source and HTML-render
  forms of one rule), and 74 are ungrounded operational rules. The preamble
  now also records that the crosswalk was last extended on 27 July 2026, so
  a reader can tell that conditions added since then are ungrounded for want
  of a re-run rather than by any judgement about them.
- **The README no longer calls `pub-check/README.md` "the full table of
  what it checks".** That file describes itself, correctly, as a
  class-level summary and covers 35 of the 58 classes; `CHECKS.md` is the
  complete catalog. `stage-uri-live` is added to the summary table.
- Check counts corrected in the README prose, the README badge, the
  repository-structure listing, and the tool README.

Releases:

- **v1.1.6, v1.1.7 and v1.1.8 were tagged and pushed but never published as
  GitHub Releases**, so the repository's Releases page showed v1.1.5 from
  10 August as the latest while the code was three releases ahead. All
  three are published from their CHANGELOG entries alongside v1.2.0.
- **The floating `v1` tag was four commits stale**, pointing at the v1.1.5
  commit. A consumer following the documented
  `uses: OASIS-Docs/publication-assurance@v1` pin was running code from
  before v1.1.6. `v1` now tracks v1.2.0.

## v1.1.8 - 2026-08-19

A patch release: no executable check changed, no check threshold moved, and the
exit-code gate contract is unchanged. It closes the gap recorded in v1.1.7, that
this repository had no test harness and so the three defects fixed that day
carried no regression fixture.

- **A regression suite under `tests/`.** `pytest`, laid out to match the sibling
  `publisher-toolkit`: a `conftest.py` that loads the checker by path (the
  `pub-check/` directory is hyphenated and cannot be imported as a package),
  on-disk defect trees under `tests/fixtures/`, and one test module per area.
  `pytest` is the only development dependency; the checker stays stdlib-only.
- **A fixture per v1.1.7 defect.** Each one was demonstrated failing against the
  parent commit before it was accepted. `test_manifest_title_unescapes_html_entities`
  fails on a9699aa with the literal `&nbsp;` in the manifest title.
  `test_manifest_preamble_omits_the_json_claim_when_no_json_ships` fails on
  5c3dd27, where `emit_manifest_txt` has no `with_json` keyword to pass.
  Five fixtures in `test_delivery_items.py` fail on 7cbe512, where
  `find_delivery_items` returns `index.html` as the delivery HTML.
- **The delivery-item fixtures use the shape that actually triggers the
  defect.** `index.html` only wins the shortest-stem fallback when no `.html`
  in the directory has a stem ending in `-<stage>`. A conforming
  `<spec>-<stage>.html` takes the exact-match branch and was never displaced.
  The fixture tree therefore re-stems a CSAF corpus package to drop the stage
  token, which is the UBL v2.5 `os/` shape, and adds a generated directory
  listing beside it. A second fixture holds the conforming shape as a
  no-change guard.
- **Coverage of the suppression direction.** The reported UBL symptom was
  blockers disappearing, not appearing: a directory listing carries none of the
  cover content the `member-uri` and `xml-namespace` checks read, so a package
  that must not publish passed silently.
  `test_a_directory_listing_does_not_suppress_cover_blockers` pins that
  direction against a cover carrying member-only Kavi URIs.
- **Smoke coverage over the entry points.** `--json` key shape and its
  blocker-count agreement, exit-code semantics on both branches, the
  `--list-checks` registry/AST parity assertion, `--emit-manifest` writing both
  companion files, and the two argument-error paths. These pin the CLI contract
  that `gate.py`, the composite action and the publication runbook consume.
- **CI runs the suite.** `.github/workflows/ci.yml` on push, pull request and
  manual dispatch. It installs `poppler-utils` so the optional PDF cross-check
  takes the same path in CI as on a maintainer's machine, and runs
  `--list-checks` as a separate step so registry drift is legible in the log.
  A red run blocks.

Blast radius of the `index.html` defect, established rather than assumed: every
publication audit and pub-check validation report held in the OASIS docs ops
workspace was swept, 120 report JSON files across KMIP, OpenEoX, XACML/ACAL,
ODF, LegalDocML, NIEMOpen and UBL. None was graded against a directory listing,
so no published verdict changes. Two conditions account for that. Most runs
selected a delivery HTML whose stem ends in `-<stage>`, which takes the
exact-match branch and never reaches the shortest-stem fallback, including the
two OpenEoX runs against a staged tree that does carry `index.html`. The three
runs that did reach the fallback pointed at directories with no `index.html` in
them. The UBL v2.5 `os` artifacts postdate 14ad114 and record `UBL-2.5.html` as
the delivery item, with the four `xml-namespace` and the `member-uri` blockers
present.

One latent exposure was found and is closed by the fix rather than by any
change here: `legaldocml/akn-core/v2.0/cs01/` holds an untracked `index.html`
beside `akn-core-v2.0-namespace.html` and no `-cs01`-suffixed HTML, so the
pre-fix tool selects the listing there. The July 2026 LegalDocML audit escaped
it only because it ran against a separate copy. The same shape recurs in the
ECF `model/` directories.

## v1.1.7 - 2026-08-19

A patch release: no executable check changed, and the exit-code gate contract
is unchanged. Two defects in the Work Product Manifest File emitter, both
found while staging UBL v2.5 as an OASIS Standard.

- **Entity leak in the manifest title.** `emit_manifest_txt` copied the
  document title out of the rendered HTML `<title>` without unescaping it, so
  any entity in the title reached the published manifest verbatim. UBL 2.5
  renders its title as `Universal Business Language Version&nbsp;2.5`, which
  produced `Title:          Universal Business Language Version&nbsp;2.5` at a
  citable URL. The title is now unescaped before whitespace is collapsed, so
  the non-breaking space folds into a normal space like any other run of
  whitespace.
- **`index.html` selected as the HTML delivery item.** `find_delivery_items`
  falls back to the shortest stem when no candidate ends in `-<stage>`, and
  `index.html` is shorter than any conforming spec filename. Every deployed
  OASIS tree carries a generated `index.html` in each directory, so running the
  gate against a live or fully staged tree selected the directory listing as
  the delivery HTML, and the cover, front-matter, title-version and asset-ref
  checks then ran against it. Symptom on UBL v2.5 os: `Delivery items do not
  share one basename: ['UBL-2.5', 'index']`, `No 'This version' URL block found
  on the HTML cover`, `Title does not incorporate a Version identifier: 'Index
  of /ubl/os-UBL-2.5/'`, plus the loss of the four `xml-namespace` and the
  `member-uri` blockers that the real cover produces. `index.html` is now
  skipped in the candidate scan: it is server-only by the publication contract
  and is never a delivery item. This affects audit-only runs most, since those
  point at a deployed tree by definition.
- **Unconditional claim of a JSON companion.** The preamble stated "the
  machine-readable companion is manifest.json in this directory" whether or
  not one was emitted. A publication that ships the text manifest alone was
  therefore shipping a dangling reference. `emit_manifest_txt` takes a
  `with_json` keyword, defaulting to `True` so `--emit-manifest` is unchanged;
  callers emitting the text manifest alone pass `False` and the sentence is
  dropped.

Known gap, recorded rather than closed: this repository has no test harness,
so neither fix carries a regression fixture. Both were verified by hand against
the UBL 2.5 OS package. Standing up a harness is separate work and should
happen before the next behavioural change to the emitter.

## v1.1.6 - 2026-08-13

A patch release: no executable check changed, and the exit-code gate contract
is unchanged. The reference markdown-to-HTML pipeline copy under `.github/src/`
is brought to parity with the canonical publisher-toolkit pandoc semantics,
closing three rendering defect classes the old flags produced:

- `-f markdown+autolink_bare_uris-implicit_figures` (was
  `+hard_line_breaks`, no `-implicit_figures`): stops pandoc wrapping bare
  image lines in `<figure>`/`<figcaption>` (alt text rendered as a visible
  caption under the logo) and stops every source newline becoming a `<br/>`.
- `--no-highlight` added: fenced code blocks render as plain
  `<pre><code>` so the stylesheet's continuous block background is not
  broken into per-token bars.
- `--toc` removed: the OASIS template carries a hand-authored, linked
  Table of Contents in the markdown source at the template position (after
  the Notices block); pandoc's template-position ToC is not wanted. The
  `DropNavBlocks` and `DropLogoFigures` transforms remain as defensive
  strips.

Verified against the repository's own corpus: converting
`examples/csaf/v2.1/csaf-v2.1.md` yields 525 fragment links with zero
unresolved anchors, the authored ToC intact, and zero figcaptions, nav
blocks, or highlight spans. The legacy monolith under `.github/src/test/`
received the same flag parity.

## v1.1.5 - 2026-08-10

A maintenance release: no executable check changed (still **169 checks,
57 classes**), and the exit-code gate contract is unchanged. `action.yml`
gains an output surface a consumer workflow was previously left to build
itself: a run page showed only the pass/fail dot, and the actual findings
were reachable only by opening raw step logs (which GitHub restricts on
some repos even for maintainers of a public fork).

Action:

- `action.yml` gains three new inputs, all additive and backward
  compatible: `report-dir` (default `pubcheck-report`; writes
  `pubcheck-report.txt`/`.json`, set to `''` to disable), `write-summary`
  (default `true`; a GitHub Step Summary section with the verdict and full
  ordered findings list), and `summary-title` (label the summary heading
  when the action is called more than once, e.g. in a matrix).
  `target`/`args`/`python-version`/`install-poppler` and the exit-code
  contract behave exactly as before.
- New outputs: `exit-code`, `blockers`, `warnings`, `report-txt`,
  `report-json`, so a caller can branch on the result without re-parsing
  logs.
- Internally the gate step now runs `continue-on-error` and a final
  "Enforce gate result" step re-raises the same exit code, so the summary
  and report-file steps run even when the gate found blockers (`if:
  always()`), while the step the caller sees still fails on a blocker,
  exactly as every release before this one.
- New `pub-check/render_summary.py`: renders the Step Summary section from
  a `--json` report (and an optional plain-text report for the full
  findings block); used by `action.yml`, also runnable standalone for a
  quick local look at a report. When `report-dir` is set (the default), the
  summary section also states the exact `pubcheck-report.txt`/`.json`
  paths written on the runner, so a caller that forgets to upload them as
  an artifact is still told where they are.

Examples:

- New `examples/consumer-workflow-matrix.yml`: a multi-package caller
  (matrix over several targets, readable job names, `report-dir` per
  package, `upload-artifact` with `if: always()`) that uses the action's
  new native output surface instead of reimplementing report capture. A
  follow-up step reads `upload-artifact@v4`'s own `artifact-url` output and
  appends a direct one-click download link to the Step Summary, so the run
  page states exactly where the report landed instead of leaving it to be
  found in the Artifacts section.

Validation: exercised end to end against a real (unpublished, pre-CSD02)
package on a fork before this PR opened: the step summary rendered the
verdict, full findings list, report file paths, and the artifact download
link; `pubcheck-report.txt`/`.json` uploaded as artifacts and downloaded
back byte-identical; the job still concluded `failure` on the package's
real blockers.

## v1.1.4 - 2026-08-05

A fix release: no new criteria (still **169 checks, 57 classes**). Two
existing checks reported findings that were defects in the gate rather than
in the package, both surfaced by a remediation run against NIEMOpen
`ndr/v6.0/ps01`. Verified against all ten packages in `examples/`: zero
findings changed on any of them.

`front-matter`, cover-page URL extraction:

- `stage_urls_from_md` terminated a URL on `)`, whitespace or a backslash,
  but not on `<`. A TC that wraps its cover-page URLs in inline HTML (NDR
  authors `<link>https://...</link>`, which its own preprocessor expands to
  an anchor) had the closing tag absorbed into the URL, so every This-stage
  and Latest-stage URL reported a false
  `points at 'link>' which is not a file in the package`. A URL never
  legitimately continues through `<`, so `<` joins the terminator set. This
  also unblocked `conformance-structure`, which could not fetch the previous
  stage while the URL was mangled.

`oasis.rules.yaml`, kept in lockstep (nide):

- `OASIS-TECHNICAL-COMMITTEE` and `OASIS-CHAIRS` encode the same two requirements
  for the authoring-time engine. Changing only the Python would have broken the
  property the README advertises, that "a green `nide quality` run at authoring
  time predicts a green intake run": an Open Project work product would have
  failed `nide quality` and passed intake. Both rules now accept the same prose
  the Python does. Both changes are strict **supersets**, verified over the
  heading set: nothing that matched before fails now, so no TC currently building
  against these rules can be broken by the change.

`template`, required front-matter sections:

- The registry required a literal `Technical Committee` heading and a
  heading beginning `Chair`. OASIS **Open Projects** are governed by a
  Project Governing Board and their template says `Open Project:` and
  `Project Chair:`, so an Open Project specification was told to supply a
  Technical Committee section it does not have and cannot honestly add.
  Both forms are now accepted, and the qualified-Chair form
  (`Project Chair`, `NTAC Technical Steering Committee Chairs`) is scoped to
  the front-matter window so a body or appendix heading ending in "Chairs"
  cannot satisfy a cover page that carries no Chairs block at all. The
  qualifier is bounded to five words, so a sentence of prose ending in the
  word cannot satisfy it either.

- The same heading also serves as a **block boundary** in twelve other places,
  where it terminates the This/Previous/Latest stage-URL blocks parsed off the
  cover. Accepting `Open Project` in the section check without accepting it
  there would have left an Open Project cover never closing its stage block,
  parsing past its intended end into whatever followed, silently and with no
  finding to say the parse had gone wrong. All twelve now route through one
  `ORG_HEADING` constant, which the section registry shares, so the wording is
  defined once.

## v1.1.3 - 2026-08-05

A maintenance release: no executable check changed (still **169 checks,
57 classes**). The action and its workflows move to the Node 24 runtimes
before GitHub retires Node 20, and the repository's scope is settled in
writing.

Action and CI runtimes:

- `action.yml` and every bundled workflow now pin `actions/checkout@v5`,
  `actions/setup-python@v6`, and `actions/setup-node@v5`. GitHub is
  deprecating the Node 20 action runtime; a consumer on the old pins would
  have started seeing runner warnings and, eventually, failures. The gate
  logic, inputs, and exit-code contract are untouched.

Distribution:

- The floating **`v1`** major tag is now published and tracks the newest
  `v1.x` release. `README.md`, `action.yml`, and
  `examples/consumer-workflow.yml` have documented
  `uses: OASIS-Docs/publication-assurance@v1` since v1.0.0, but no such tag
  existed, so a TC copying the Quick start hit `Unable to resolve action`.
  The documented usage now resolves.

Scope:

- The step 6.0 deploy engine, the central dispatcher, and `index_audit.py`
  live in `OASIS-Docs/publisher-toolkit`, not here. This repository is the
  publication acceptance criteria and the `oasis-pub-check` gate; the
  toolkit consumes the gate as a public action. (These files were briefly
  added and then moved during the 30 July work; the net change to this
  repository is zero, and the commits are squashed away.)

Documentation:

- Figure footnotes in the architecture diagrams drop the "X, not Y"
  construction; the SVG sources and their exported PNGs are regenerated in
  step so the raster and vector twins stay identical.

## v1.1.2 - 2026-07-28

A documentation release: no executable check changed (still **169 checks,
57 classes**). The README now leads with a Quick start so a TC can run the
gate before reading anything else.

Documentation:

- New **Quick start** at the top of the README: the local one-command run
  (`oasis_pub_check.py <package>`) and the GitHub Actions path (copy
  `examples/consumer-workflow.yml` into the TC repo and run it from the
  Actions tab), with the minimal workflow step shown inline.
- New **guides table** mapping each companion document
  (`PUBLICATION-QUALITY.md`, `pub-check/README.md`, `CHECKS.md`,
  `TRANSFORMS.md`, `AUTHORITIES.md`, and the worked example) to the moment a
  TC reaches for it.
- The reference sections (what the gate checks, provenance, validation and
  audit, nide, layout, license) move below the Quick start with their
  content unchanged; `action.yml` and `examples/consumer-workflow.yml` are
  added to the layout tree.

## v1.1.1 - 2026-07-27

Commits `fc94fe0`, `bd0481b`, `3633a49` - driven by
[#2](https://github.com/OASIS-Docs/publication-assurance/issues/2):
the policy-authority catalog was pinned to the 96-condition July snapshot
while the registry had grown to 169. No executable check changed
(still **169 checks, 57 classes**); this is a provenance and documentation
completion.

Provenance:

- `AUTHORITIES.md` / `authorities.yaml` extended from the 96-condition
  snapshot to the full registry: **93 of the 169 checks now trace to a
  verbatim clause** of written OASIS policy (was 38). Eight new acceptance
  criteria (`AC-CONTENT-09/10/11`, `AC-NAMING-31/32/33`,
  `AC-PACKAGING-24/25`), each grounded in a verbatim corpus substring and
  adversarially reviewed; every quote mechanically re-verified. The stale
  "original 96 / folding outstanding" caveat is gone; the README count and
  the provenance diagram are regenerated to match.

Documentation:

- The OpenEoX eox-core v1.0 csd01 worked example re-run against the current
  169-check tool (0 blockers; 12 warnings, 9 informational; publishable).
- The CSAF regression corpus (`csaf/`, `csaf-cvrf/`) moved under
  `examples/`, alongside the worked example; pure git-mv renames.
- Authored references to Stefan Hagen now link to his GitHub profile.

## v1.1.0 - 2026-07-25

Commit `7431c2d` - driven by
[#1](https://github.com/OASIS-Docs/publication-assurance/issues/1):
public-review comments on KMIP Usage Guide v3.0 cnd01 surfaced editorial
defect classes the gate did not cover. **165 -> 169 checks, 55 -> 57
classes.**

New criteria:

- `link-mismatch` extended to the rendered HTML on every track (BLOCKER):
  anchor text that displays a URL must agree with its href. Catches
  display/target divergence that live link crawls pass over because the
  href resolves while the visible citation is wrong.
- `ref-rfc` (WARN, new class): an `[RFCnnnn]` references entry's label,
  body-text number, and ietf.org / rfc-editor.org URL number must agree,
  compared as integers so zero-padded canonical URLs agree with unpadded
  labels. Excuse vocabulary for obsoletes/supersedes/updated-by phrasing.
- `boilerplate-dup` (WARN, new class): the template's "send comments"
  status paragraph appears exactly once. Mirrored to the nide rules file
  as `OASIS-COMMENTS-PARA-DUP`; the other two criteria compare two
  captured values and stay pub-check-only (`pub-check/rules/README.md`).

Fixes:

- `run()` invoked several checks repeatedly (residue twice, image-policy
  twelve times), so single defects were reported as doubles in shipped
  validation reports. Call list deduplicated; `Findings.add` suppresses
  identical repeats as a backstop.
- `stage-token` no longer warns on Previous-version cover links that
  correctly carry the linked publication's own approved stage token
  (`cn01` for a cnd draft, `cs01` for a csd draft).
- The check counts shown in the architecture diagrams were corrected to
  match `--list-checks` rather than a hardcoded figure.

Validation: 12-package regression corpus byte-diffed before and after
(zero new findings, exit codes unchanged); two independent adversarial
review passes before merge.

## v1.0.1 - 2026-07-24

Commits `34a1067`, `d4642be`: architecture diagrams and their PNG exports
corrected to the actual 165-check / 55-class inventory (stale hardcoded
counts). No criteria changes.

## v1.0.0 - 2026-07-24

Commit `01b87ff`: initial public release of the repository as the
self-contained master for the OASIS publication acceptance criteria.
**165 checks across 55 classes**: `oasis_pub_check.py` (the executable
gate), the generated criteria catalog `CHECKS.md`, the policy authority
mapping (`AUTHORITIES.md`, `authorities.yaml`), the nide rules bridge
(`pub-check/rules/`), the manifest contract, the CSAF / CSAF-CVRF
regression corpus, and the consumer GitHub Action. Earlier iterations
(91/92-check era and up) predate this repository's public history and are
recorded in the internal working history only.
