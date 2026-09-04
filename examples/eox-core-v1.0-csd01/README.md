<!--
Copyright (c) OASIS Open 2026. All Rights Reserved.
This directory contains the quality record of an OASIS
publication, reproduced verbatim as a worked example.
-->

# Worked example: OpenEoX EoX-Core v1.0 CSD01

The Validation Report for
[OpenEoX Core Schema Version 1.0 CSD01](https://docs.oasis-open.org/openeox/eox-core/v1.0/csd01/eox-core-v1.0-csd01.html),
published 13 July 2026 and filed on
[TCADMIN-4725](https://issues.oasis-open.org/browse/TCADMIN-4725).
This is the standard record every TC receives for every publication.

| File | What it is |
|---|---|
| `eox-core-v1.0-csd01-pub-check-validation-2026-07-27.md` / `.pdf` | The Validation Report: all 169 conditions across the 57 check classes in force on 27 July 2026, each with the value the tool pulled from the package set against the value it was compared to. Zero blockers; 12 warnings and 9 informational notes, triaged in the header. The criteria set has grown since; the current one is [`pub-check/CHECKS.md`](../../pub-check/CHECKS.md). |

Running `oasis_pub_check.py` yourself gives you the
findings, the exit code, and with `--json` the full per-condition record
(the same conditions, observed values, and comparisons shown in this
report). The formatted report is rendered by TC Administration at intake from that same
per-condition data and filed to your ticket.

The publication is also audited at the event level (15 mandatory gates:
byte identity, index chains, announcements, an independent adversarial
verifier); that Publication Audit Report is a TC Administration operational
record filed to the ticket. This example carries only the Validation Report.

The publication's history shows what the gate catches: the TC's first release
candidate carried 13 blockers, the same set the manual intake review found.
The third release candidate ran clean and was published.

The acceptance criteria grow as correction rounds surface new failure modes,
so a report is always read against the inventory named in its own header.

---

**The documentation set:** [Repository overview](../../README.md) · [TC guide](../../PUBLICATION-QUALITY.md) · [The acceptance criteria tool](../../pub-check/README.md) · [The criteria catalog](../../pub-check/CHECKS.md) · [The pipeline, command by command](../../TRANSFORMS.md) · [Architecture diagrams](../../assets/architecture/README.md)
