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
rules with `nide quality` and fails the build on any BLOCKER. The two-file
convention is nide's design: the organisation file is fetched from here and
left unchanged locally; the spec file carries TC- and spec-specific rules on
top. The rules-as-data interface and the first version of this file came from
[Stefan Hagen](https://github.com/sthagen)'s work bridging nide to the
acceptance criteria in this repository.

## Contract

- TC repositories take this file verbatim. Local edits belong in the
  spec-level rules file.
- Rule ids are stable and permanent. The `OASIS-` prefix is reserved for
  this file; a retired rule is dropped and its id retired with it.
- The severity vocabulary is `BLOCKER` and `WARN`. A BLOCKER fails the
  build (exit 1); a WARN reports and passes (unless run `--strict`).
- This file is a subset of the gate. It carries the conditions expressible
  against the assembled document as the authoring engine sees it, before
  rendering. The full acceptance criteria remain
  [`oasis_pub_check.py`](../oasis_pub_check.py) and its generated catalog
  [`CHECKS.md`](../CHECKS.md), which also verify the rendered artifacts
  (HTML, PDF, schemas, package layout) a source-side rules engine
  cannot reach. A green `nide quality` run predicts a green gate run; the
  full gate still runs at intake.

## Rule allocation between nide and pub-check

Every checkable requirement, or requirement-fragment, is assigned to exactly
one home. If a requirement is checkable on the document **prose** as the
author writes it (headings, body text, links, RFC 2119 usage), it becomes a
nide rule in this file, so nide catches it at authoring time. If it can only
be checked on the **delivered package** (filenames on disk, published URIs,
cross-file agreement, PDF fonts, the zip, multi-part layout), it stays
exclusively in pub-check Python. A criterion that
spans both domains contributes its safe, source-provable subset here and names
the rest explicitly as `pub_check_only` in the authority-mapping record. A rule
is added here only after it is evaluated against the published corpus.

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
| OASIS-RESID-TEMPLATE-INSTRUCTION | BLOCKER | residue |
| OASIS-COMMENTS-PARA-DUP | WARN | boilerplate-dup |
| OASIS-LINK-DEAD-LISTS | WARN | dead-lists |
| OASIS-LINK-DOUBLE-SLASH | WARN | double-slash |
| OASIS-MEMBER-URI | BLOCKER | member-uri |
| OASIS-REFERENCES-SPLIT | WARN | references-split |

The set grows the same way the acceptance criteria grow: a defect that
reaches intake and is expressible as a source-side rule is added here so
the next TC catches it at authoring time.

Two source-text criteria from the same correction round as
OASIS-COMMENTS-PARA-DUP stay pub-check-only because they compare two
captured values, which a single-pattern rule cannot express: `ref-rfc`
(an [RFCnnnn] references entry's label, body number, and URL number must
agree) and the rendered-HTML half of `link-mismatch` (anchor text that
displays a URL must agree with its href).
