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
- `assets/build.py` derives the diagram check counts from `--list-checks`
  instead of hardcoding them.

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
