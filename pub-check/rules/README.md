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

# The organisation rules file: the acceptance criteria as data

**Author: Michael Coletta, Technical Advisor, OASIS Open**

`oasis.rules.yaml` in this directory is the OASIS baseline quality-rules
file for Standards Track Work Products, expressed as data so that TC-side
authoring engines can evaluate the rules during every build, long before a
package reaches intake.

This file is the canonical upstream copy. TC repositories consume it by
copying it unchanged next to their own spec-level rules file and extending
it:

```yaml
# etc/rules/spec.rules.yaml in the TC repository
meta:
  name: my-spec-rules
  extends: oasis        # merges etc/rules/oasis.rules.yaml first
```

The [`nide`](https://codes.dilettant.life/docs/nide/) authoring engine
(used by the CSAF, DPS, SARIF, OpenEoX, and MQTT TCs) evaluates these
rules with `nide quality`, failing the build on any BLOCKER. The two-file
convention is nide's design: the organisation file is fetched from here and
never edited locally; the spec file carries TC- and spec-specific rules on
top. Credit where due: the rules-as-data interface and the first cut of
this file came from Stefan Hagen's work bridging nide to the acceptance
criteria in this repository.

## Contract

- **Copy unchanged.** TC repositories take this file verbatim. Local edits
  belong in the spec-level rules file, never here.
- **Rule ids are stable.** The `OASIS-` prefix is reserved for this file.
  Ids are never renamed or reused; a retired rule is removed, not
  repurposed.
- **Severity vocabulary is `BLOCKER` and `WARN`.** A BLOCKER fails the
  build (exit 1); a WARN reports and passes (unless run `--strict`).
- **This file is a subset, not the gate.** It carries the conditions
  expressible in a rules engine that reads the assembled document IR. The
  full acceptance criteria remain
  [`oasis_pub_check.py`](../oasis_pub_check.py) and its generated catalog
  [`CHECKS.md`](../CHECKS.md), which also verify the rendered artifacts
  (HTML, PDF, schemas, package layout) that no source-side rules engine
  can see. A green `nide quality` run predicts a green gate run; it never
  substitutes for it.

## How the rules map to the acceptance criteria

| Rule id | Severity | Acceptance-criteria class ([CHECKS.md](../CHECKS.md)) |
|---|---|---|
| OASIS-SCOPE | BLOCKER | template |
| OASIS-CONFORMANCE | BLOCKER | template |
| OASIS-TECHNICAL-COMMITTEE | BLOCKER | front-matter |
| OASIS-CHAIRS | WARN | front-matter |
| OASIS-EDITORS | WARN | front-matter |
| OASIS-ABSTRACT | BLOCKER | template |
| OASIS-LOGO | WARN | logo |
| OASIS-RFC-2119-CITED | BLOCKER | rfc-keywords |
| OASIS-RFC-8174-PAIRED | WARN | rfc-keywords |
| OASIS-RESID-TODO | BLOCKER | residue |
| OASIS-RESID-TBD | WARN | residue |
| OASIS-RESID-FILL-IN | WARN | residue |
| OASIS-LINK-DEAD-LISTS | WARN | dead-lists |
| OASIS-LINK-DOUBLE-SLASH | WARN | double-slash |

The set grows the same way the acceptance criteria grow: a defect that
reaches intake and is expressible as a source-side rule is added here so
the next TC catches it at authoring time.
