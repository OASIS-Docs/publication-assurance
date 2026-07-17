#!/usr/bin/env python3
# Copyright 2026 OASIS Open
# SPDX-License-Identifier: Apache-2.0
# Authored by Michael Coletta, Technical Advisor to OASIS Open.
"""Generate CHECKS.md, the OASIS publication acceptance criteria, from oasis_pub_check.py itself.

The catalog is rendered from the tool's own condition registry
(conditions_inventory(), which asserts the registry and the AST agree in
both directions), so the documentation cannot drift from the implementation.
Rerun after any change to the checks:

  python3 render_checks_md.py        # rewrites CHECKS.md next to this script
"""
from __future__ import annotations

import importlib.util
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent

NOTICE = """\
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
"""

INTRO = """\
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

{total} conditions across {classes} check classes.

## Legend

| Field | Values |
|---|---|
| Severity | **BLOCKER**: the package cannot publish until fixed (exit 1). **WARN**: publishable, flagged for the record, often a must-fix before a later stage. **INFO**: recorded, no action required. |
| Applies | **both**: every package, regardless of input format. **md** / **docx** / **odt**: add-on conditions that engage only when that source format is present; on any other package they report NA with the reason, never a silent pass. There is no closed list of input formats: DocBook/XML, LaTeX, and any other source are validated through the **both** conditions, with the cover parsed from the rendered HTML. Deeper render-fidelity add-ons grow the same way the existing tracks did, calibrated against the published corpus. |
| Requires | A package or environment feature (network, `pdftotext`, `pdffonts`, shipped schemas, a shipped manifest) without which the condition reports NA in the validation report, never a silent pass. |
"""

FOOTER = """\
---

Generated from `oasis_pub_check.py` by `render_checks_md.py`. The inventory is
asserted from the code: `python3 oasis_pub_check.py --list-checks` fails if the
registry and the implementation disagree in either direction.

**The documentation set:** [Repository overview](../README.md) · [TC guide](../PUBLICATION-QUALITY.md) · [The acceptance criteria tool](README.md) · [Worked example](../examples/eox-core-v1.0-csd01/README.md) · [The pipeline, command by command](../TRANSFORMS.md) · [Architecture diagrams](../assets/architecture/README.md)
"""

# One-line description per check class, keyed by class name. A new class
# added to pub_check.py without a line here fails the render (KeyError),
# which is the point: the catalog stays complete by construction.
CLASS_DESCRIPTIONS = {
    "asset-refs": "Relative files the HTML references must ship in the package.",
    "case": "The publication host is case-sensitive; canonical paths are lowercase.",
    "cover-hr": "A horizontal rule above the title opens the OASIS-rendered PDF with a blank page.",
    "date-sync": "The markdown, HTML, and copyright dates must describe the same revision.",
    "dead-lists": "Mail addresses at lists.oasis-open.org fail silently; comments go through Higher Logic.",
    "double-slash": "A double slash inside a relative path 404s on the CDN.",
    "fence-collapse": "An opening code fence with trailing text collapses the whole block under pandoc.",
    "filenames": "Delivery items are named for the published stage, one basename, all formats present.",
    "front-matter": "The This/Latest stage URL blocks must match the package's real publish path.",
    "generator": "DOCX-native renders must come from Microsoft Word, matching the TC's precedent.",
    "html-anchors": "Every internal fragment link must resolve to an anchor in the document.",
    "html-residue": "Pipeline residue in the HTML: duplicate title H1, stale pandoc header, CI paths.",
    "html-title": "The HTML title element must be a real document title with no working residue.",
    "image-policy": "Images must be self-contained, inert, and within the pipeline's size caps.",
    "junk-files": "OS and editor junk must not ship in the package.",
    "link-mismatch": "A visible URL and its link target must agree.",
    "logo": "The cover logo should be the canonical OASIS template logo.",
    "manifest": "A shipped manifest.json must verify against the files on disk.",
    "md-links": "Markdown link forms that render wrong under pandoc autolinking.",
    "odt-integrity": "The ODT source must be a valid, macro-free OpenDocument container.",
    "package-refs": "Files the document cites under its own stage path must ship in the package.",
    "pdf-cover": "The rendered PDF cover must carry the title exactly once and no CI paths.",
    "pdf-fonts": "PDF embedded fonts are compared against the package's own CSS as typography authority.",
    "pdf-sync": "The PDF must be readable and rendered from the same revision as the rest of the package.",
    "previous-stage": "Second and later stages must cite the previous stage's URLs.",
    "residue": "Editor placeholders (TODO, tbd, 'Will be filled in') must not ship.",
    "revision-collision": "A new submission must not collide with a stage already live for the version.",
    "rfc-keywords": "Normative key words require the RFC 2119 (and 8174) citations.",
    "schema-id": "Every JSON schema's $id must agree with where the file actually publishes.",
    "stage-name": "The stage token must be a current, correctly numbered stage per the Naming Directives.",
    "symlinks": "Self-referential symlinks materialize into unbounded recursion on deploy.",
    "template": "The OASIS template's required front-matter sections, in order, plus Conformance.",
    "template-css": "The HTML must carry a stylesheet; the canonical CSS is the default expectation.",
    "version-naming": "The version directory and delivery filenames must agree on one vN.N(.N) version.",
    "vml-fallback": "VML-only images in Word HTML renders are invisible in every modern browser.",
}


def esc(s: str) -> str:
    return s.replace("|", "\\|").replace("<", "&lt;").replace(">", "&gt;")


def main() -> None:
    spec = importlib.util.spec_from_file_location("pub_check", HERE / "oasis_pub_check.py")
    pc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pc)
    inv = pc.conditions_inventory()   # raises on registry/AST drift

    classes = sorted({c["check"] for c in inv})
    counts = Counter(c["check"] for c in inv)
    lines = [NOTICE, INTRO.format(total=len(inv), classes=len(classes))]

    n = 0
    for cls in classes:
        lines.append(f"### {cls}\n")
        lines.append(CLASS_DESCRIPTIONS[cls] + "\n")
        lines.append("| # | Condition verified | Value pulled (observed) | "
                     "Compared against | Severity | Applies | Requires |")
        lines.append("|---|---|---|---|---|---|---|")
        for c in [c for c in inv if c["check"] == cls]:
            n += 1
            lines.append(
                f"| {n} | {esc(c['condition'])} | {esc(c['pulls'])} | "
                f"{esc(c['compares_to'])} | {c['severity']} | {c['applies']} | "
                f"{c.get('requires', '-')} |")
        lines.append("")

    lines.append(FOOTER)
    out = HERE / "CHECKS.md"
    out.write_text("\n".join(lines))

    text = out.read_text()
    rows = sum(1 for ln in text.splitlines()
               if ln.startswith("| ") and ln.split("|")[1].strip().isdigit())
    sections = sum(1 for ln in text.splitlines() if ln.startswith("### "))
    assert rows == len(inv), f"{rows} rows rendered, {len(inv)} in inventory"
    assert sections == len(classes), f"{sections} sections, {len(classes)} classes"
    print(f"wrote CHECKS.md: {rows} conditions, {sections} classes")


if __name__ == "__main__":
    main()
