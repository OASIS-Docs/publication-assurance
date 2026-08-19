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
package on a fork before this PR opened — step summary rendered the
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
