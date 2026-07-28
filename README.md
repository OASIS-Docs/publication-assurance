<!--
Copyright 2025-2026 OASIS Open
SPDX-License-Identifier: Apache-2.0
Authored by Michael Coletta, Technical Advisor to OASIS Open.
-->

![OASIS Publication Assurance](assets/hero.png?v=169)

<p align="center">
  <a href="LICENSE"><img alt="Code: Apache-2.0" src="https://img.shields.io/badge/code-Apache--2.0-2c4a8a"></a>
  <a href="NOTICE"><img alt="Criteria prose: OASIS verbatim-only" src="https://img.shields.io/badge/criteria_prose-OASIS_verbatim--only-446CAA"></a>
  <img alt="Python 3.10+" src="https://img.shields.io/badge/python-3.10%2B-3776ab">
  <img alt="Dependencies: stdlib only" src="https://img.shields.io/badge/gate_dependencies-stdlib_only-2f9e44">
  <img alt="Checks: 169 individual, 57 classes" src="https://img.shields.io/badge/checks-169_individual_%C2%B7_57_classes-f08c00">
  <img alt="Regression corpus: 13 packages" src="https://img.shields.io/badge/regression_corpus-13_packages-6741d9">
</p>

**Author: Michael Coletta, Technical Advisor, OASIS Open**

This repository is the gate OASIS TC Administration runs on every work product
before it is published to `docs.oasis-open.org`. `oasis-pub-check` is that same
gate, packaged so your TC can run it on your own package, in your own repo,
before you vote. Fix problems while the document is still yours.

---

## Quick start

The gate is one Python file (`pub-check/oasis_pub_check.py`), standard library
only, no install and no config. `<package>` is either a stage directory or a
`.zip`. **Exit `0` means publishable.** Run it two ways.

### 1. On your machine

```bash
git clone https://github.com/OASIS-Docs/publication-assurance
python3 publication-assurance/pub-check/oasis_pub_check.py <package>
```

That is the whole thing. Add `--json` for machine-readable output, or
`--emit-manifest` to also write the release manifest.

![oasis-pub-check gate](assets/gate.png?v=169)

### 2. In your TC repo on GitHub (one file, three clicks)

1. Copy [`examples/consumer-workflow.yml`](examples/consumer-workflow.yml) into
   your TC repo as `.github/workflows/pub-check.yml`.
2. Commit and push.
3. In your repo on GitHub: **Actions → pub-check → Run workflow**, type your
   package path (e.g. `work/v1.0/csd01`), and run.

A blocker turns the build red; warnings do not fail it. You copy no engine code
into your repo, so you pick up fixes by bumping the version tag.

If you would rather paste a step than copy the file, this is the minimum:

```yaml
name: pub-check
on:
  workflow_dispatch:
    inputs:
      target:
        description: "stage dir or .zip"
        required: true
jobs:
  pub-check:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@v4
      - uses: OASIS-Docs/publication-assurance@v1   # for production, pin to a full commit SHA
        with:
          target: ${{ inputs.target }}
```

Inputs: `target` (required), `args` (e.g. `--json`), `python-version`,
`install-poppler`. To also run the gate automatically on every push, set
`PUB_CHECK_TARGET` in the copied workflow file and uncomment its `push:` trigger.

---

## The guides you'll actually open

| File | Open it when |
|---|---|
| **[PUBLICATION-QUALITY.md](PUBLICATION-QUALITY.md)** | You are an editor or chair and want the whole picture: both review layers, all 15 audit gates, and a worked example. **Start here.** |
| **[pub-check/README.md](pub-check/README.md)** | You want the full table of what the gate checks, with severities and the regression corpus. |
| **[pub-check/CHECKS.md](pub-check/CHECKS.md)** | The gate flagged something and you want the exact check that fired. Full catalog, generated from the code. |
| **[TRANSFORMS.md](TRANSFORMS.md)** | You build from Markdown and want the publishing pipeline command by command. |
| **[pub-check/AUTHORITIES.md](pub-check/AUTHORITIES.md)** | You want the OASIS rule behind a check, quoted verbatim, with its source. The criterion-to-clause map. |
| **[examples/eox-core-v1.0-csd01/](examples/eox-core-v1.0-csd01/README.md)** | You want to see a real Validation Report from a live publication. |

---

## What the gate checks

The 169 individual checks (57 check classes; `--list-checks` asserts the
inventory from the code) cover six areas:

- **Naming and stages**: stage tokens, version directories, filename
  conventions, live revision-collision probing, case sensitivity
- **Front matter and links**: This/Latest URL consistency, internal anchors,
  cited-but-missing files, link-target mismatches, double-slash paths,
  dead `lists.oasis-open.org` addresses
- **Content residue**: editor placeholders, stale headers, working titles,
  the pandoc autolink trap
- **Rendering and sync**: PDF-vs-source sync, embedded fonts vs the
  package's own stylesheet, image policy, Word and ODT source fidelity
- **Template and policy**: required sections, the TC Process Conformance
  requirement, RFC 2119/8174 citation
- **Package hygiene**: junk files, symlinks, schema `$id` vs publish path,
  manifest sha256, ODT container integrity

Every expectation is derived from the package itself (its own front matter, its
own CSS, its own schema `$id`s). The criteria come from OASIS publication work
across CSAF, KMIP, PKCS#11, OpenEoX, NIEM, Akoma Ntoso and LegalDocML, DMLex,
UBL, Electronic Court Filing, STIX, OSLC, Virtio, DPS, ACAL, and OpenDocument,
in every authoring format those TCs use. Each check is sourced from written
OASIS policy (the TC Process, Naming Directives v1.7, and the TC Handbook) or a
correction round in that work, and is calibrated against a regression corpus of
submissions in their original received form (including one known-bad release
candidate whose 13 blockers it reproduces exactly).

## Where the criteria come from

![How a criterion is sourced from policy](assets/authority.png?v=169)

Every acceptance criterion cites the rule it enforces. 93 of the 169 checks
trace to a verbatim clause in the governing corpus (25 pages, snapshotted and
hashed); the rest are operational rules from correction rounds. The full
criterion-to-clause map, with the exact quoted text and its source, is
[`AUTHORITIES.md`](pub-check/AUTHORITIES.md).

## Where the gate sits: validation and audit

![Validation and audit dovetail](assets/architecture/validation-audit-dovetail.png?v=169)

The two layers share one engine. Your TC runs oasis-pub-check in its own CI to
check all 169 conditions, each reported as the value the tool pulled from the
package set against the value it was compared to, in full. TC Administration
re-runs the identical code at intake (checklist step 4b) and wraps it with the
15 mandatory audit gates only a human or a live check can do: byte identity
against the published site, render class against the TC's own precedent, the
live roster, directory index chains, announcement channels, and an independent
adversarial verifier. Both reports are filed to the TC's ticket and the
internal audit record.

If the package includes a `manifest.json` conforming to
[pub-check/manifest-schema.json](pub-check/manifest-schema.json) (per file:
sha256 and role; plus source commit and tool versions), OASIS intake can verify
it directly: the TC's build records what it produced, the gate checks it against
the criteria, and the manifest lets every later step verify both.

## Interoperating with nide

The acceptance criteria are also consumed at authoring time.
[Stefan Hagen](https://github.com/sthagen)'s
[`nide`](https://codes.dilettant.life/docs/nide/) engine, which several TCs use
to author and build their specifications, reads the shared
[`oasis.rules.yaml`](pub-check/rules/oasis.rules.yaml) via `extends: oasis` and
runs the source-expressible rules with `nide quality` before the TC votes, then
emits a `nide-manifest` that pub-check hash-verifies at intake. A green
`nide quality` run at authoring time predicts a green intake run, and the
manifest lets intake confirm the published bytes match the build the TC
approved.

![How pub-check dovetails with nide](assets/architecture/nide-bridge.png?v=169)

## Repository structure

<details>
<summary>Full layout</summary>

```
publication-assurance/
├── CHANGELOG.md                     # Versioned audit trail: which issue drove which criteria
├── action.yml                       # The drop-in GitHub Action a TC calls in one step
├── pub-check/                       # The acceptance criteria
│   ├── oasis_pub_check.py           #   169 individual checks in 57 classes, stdlib only
│   ├── CHECKS.md                    #   the acceptance criteria catalog, generated from the code
│   ├── AUTHORITIES.md               #   the criterion-to-clause map (verbatim OASIS policy)
│   ├── render_checks_md.py          #   the generator (keeps CHECKS.md in sync)
│   ├── manifest-schema.json         #   provenance manifest contract
│   └── README.md                    #   checks, severities, corpus (canonical criteria)
├── PUBLICATION-QUALITY.md           # The TC-facing guide: both layers, all gates
├── examples/                        # Worked example + the regression corpus
│   ├── consumer-workflow.yml        #   the drop-in TC workflow (copy this)
│   ├── eox-core-v1.0-csd01/         #   the Validation Report from a publication
│   ├── csaf/                        #   archived CSAF work products (v2.0 lineage, v2.1 csd01)
│   └── csaf-cvrf/                   #   archived CSAF-CVRF v1.2 work products
├── TRANSFORMS.md                    # The pipeline, command by command (canonical criteria)
├── assets/                          # The diagrams (PNG)
├── .github/
│   ├── src/                         # Pipeline source (pandoc + BeautifulSoup post-processing,
│   │                                #   HTML preprocessor, wkhtmltopdf renderer)
│   ├── scripts/                     # Shell entry points used by the workflows
│   ├── styles/                      # OASIS markdown-styles CSS lineage (v1.1 → v1.8.1)
│   └── workflows/                   # step_1 (MD→HTML), step_2 (HTML→PDF),
│                                    #   step_3 (zip), pub-check (the gate)
├── LICENSE                          # Apache-2.0 (software tier)
└── NOTICE                           # The three-tier IP statement
```

</details>

## Key technologies

Python 3.10+ · Pandoc · BeautifulSoup4 · Prettier · wkhtmltopdf (this repository)
/ headless Chrome + CSS Paged Media (current production) · GitHub Actions ·
poppler (`pdftotext`/`pdffonts`, optional, for the PDF cross-checks)

## License

Three tiers, stated precisely in [NOTICE](NOTICE):

1. **Software** (the document-processing pipeline under `.github/` and the
   pub-check gate under `pub-check/`) is licensed under the
   [Apache License, Version 2.0](LICENSE).
   Copyright OASIS Open. Authored by Michael Coletta, Technical Advisor to
   OASIS Open. Every source file carries an SPDX header.
2. **Acceptance-criteria documentation** (`TRANSFORMS.md`,
   `PUBLICATION-QUALITY.md`, `pub-check/README.md`, and the generated
   `pub-check/CHECKS.md`) is Copyright OASIS Open, All Rights Reserved:
   verbatim distribution is permitted with notices retained; derivative
   works require prior written authorization from OASIS Open. These
   documents are the canonical statement of the OASIS publication
   acceptance criteria.
3. **Archived OASIS specification packages** (`examples/csaf/`, `examples/csaf-cvrf/`) are
   OASIS Work Products and retain their own published OASIS copyright, IPR,
   and license notices. Nothing in this repository relicenses them.

The OASIS name and logo are trademarks of OASIS Open.

---

**Repository maintained by**: Michael Coletta, Technical Advisor, OASIS Open  
**Contact**: michael.coletta@oasis-open.org (OASIS TC Administration)  
**Documentation**: [PUBLICATION-QUALITY.md](PUBLICATION-QUALITY.md) for the full guide, [TRANSFORMS.md](TRANSFORMS.md) for the pipeline, [pub-check/](pub-check/) for the publication gate, individual specification folders for spec-level detail

---

**The documentation set:** [TC guide](PUBLICATION-QUALITY.md) · [The acceptance criteria tool](pub-check/README.md) · [The criteria catalog](pub-check/CHECKS.md) · [Worked example](examples/eox-core-v1.0-csd01/README.md) · [The pipeline, command by command](TRANSFORMS.md) · [Architecture diagrams](assets/architecture/README.md)
