<!--
Copyright 2025-2026 OASIS Open
SPDX-License-Identifier: Apache-2.0
Authored by Michael Coletta, Technical Advisor to OASIS Open.
-->

![OASIS Publication Assurance](assets/hero.png?v=170)

<p align="center">
  <a href="LICENSE"><img alt="Code: Apache-2.0" src="https://img.shields.io/badge/code-Apache--2.0-2c4a8a"></a>
  <a href="NOTICE"><img alt="Criteria prose: OASIS verbatim-only" src="https://img.shields.io/badge/criteria_prose-OASIS_verbatim--only-446CAA"></a>
  <img alt="Python 3.10+" src="https://img.shields.io/badge/python-3.10%2B-3776ab">
  <img alt="Dependencies: stdlib only" src="https://img.shields.io/badge/gate_dependencies-stdlib_only-2f9e44">
  <img alt="Checks: 170 individual, 58 classes" src="https://img.shields.io/badge/checks-170_individual_%C2%B7_58_classes-f08c00">
  <img alt="Regression corpus: 12 packages" src="https://img.shields.io/badge/regression_corpus-12_packages-6741d9">
</p>

**Author: Michael Coletta, Technical Advisor, OASIS Open**

Before OASIS publishes a work product to `docs.oasis-open.org`, TC
Administration runs it through the publication acceptance tests.
`oasis-pub-check` is those tests, packaged to run in your own CI. Run them
before your TC votes, and fix what they find while the document is still
yours to change.

---

## Quick start

`oasis-pub-check` is one Python file (`pub-check/oasis_pub_check.py`), standard
library only, no install, no config. `<package>` is a stage directory or a
`.zip`. **Exit `0` means publishable.** Two ways to run it:

### 1. On your machine

```bash
git clone https://github.com/OASIS-Docs/publication-assurance
python3 publication-assurance/pub-check/oasis_pub_check.py <package>
```

Add `--json` for machine-readable output, or `--emit-manifest` to also
write the release manifest.

![oasis-pub-check output](assets/gate.png?v=170)

### 2. In your TC repo on GitHub

1. Copy [`examples/consumer-workflow.yml`](examples/consumer-workflow.yml) into
   your TC repo as `.github/workflows/pub-check.yml`.
2. Commit and push.
3. In your repo on GitHub: **Actions → pub-check → Run workflow**, type your
   package path (e.g. `work/v1.0/csd01`), and run.

A blocker fails the build; warnings do not. The workflow pulls `oasis-pub-check`
from this repo as a pinned Action, so you copy nothing into your repo and get
fixes by bumping the tag.

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
`install-poppler`, `report-dir` (default `pubcheck-report`; writes
`pubcheck-report.txt` and `pubcheck-report.json` there, `''` to disable),
`write-summary` (default `true`; writes a GitHub Step Summary carrying the
verdict and the full findings list, so nobody has to open the raw log), and
`summary-title` (labels that summary heading when the action is called more
than once, in a matrix for example). See
[`examples/consumer-workflow-matrix.yml`](examples/consumer-workflow-matrix.yml)
for a multi-package caller that uploads the reports as a downloadable
artifact. To also run it automatically on every push, set
`PUB_CHECK_TARGET` in the copied workflow file and uncomment its `push:` trigger.

---

## The documents

| File | Open it when |
|---|---|
| **[PUBLICATION-QUALITY.md](PUBLICATION-QUALITY.md)** | Editor or chair who wants the whole picture: both review layers, all 15 audit gates, a worked example. **Start here.** |
| **[pub-check/README.md](pub-check/README.md)** | The class-level summary of what it checks, with severities and the regression corpus. |
| **[pub-check/CHECKS.md](pub-check/CHECKS.md)** | A check fired and you want the exact one. Full catalog, generated from the code. |
| **[TRANSFORMS.md](TRANSFORMS.md)** | Building from Markdown and want the pipeline command by command. |
| **[pub-check/AUTHORITIES.md](pub-check/AUTHORITIES.md)** | The OASIS rule behind a check, quoted verbatim with its source. The criterion-to-clause map. |
| **[examples/eox-core-v1.0-csd01/](examples/eox-core-v1.0-csd01/README.md)** | A real Validation Report from a live publication. |

---

## Publication acceptance test cases: an overview

The 170 individual checks (58 check classes; `--list-checks` asserts the
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

![How a criterion is sourced from policy](assets/authority.png?v=170)

Every acceptance criterion cites the rule it enforces. 96 of the 170 checks
trace to a verbatim clause in the governing corpus (25 pages, snapshotted and
hashed); the rest are operational rules from correction rounds. The full
criterion-to-clause map, with the exact quoted text and its source, is
[`AUTHORITIES.md`](pub-check/AUTHORITIES.md).

## Where the gate sits: validation and audit

![Validation and audit dovetail](assets/architecture/validation-audit-dovetail.png?v=170)

The two layers share one engine. Your TC runs oasis-pub-check in its own CI to
check all 170 conditions, each reported as the value the tool pulled from the
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

![How pub-check dovetails with nide](assets/architecture/nide-bridge.png?v=170)

## Repository structure

<details>
<summary>Full layout</summary>

```
publication-assurance/
├── CHANGELOG.md                     # Versioned audit trail: which issue drove which criteria
├── action.yml                       # The drop-in GitHub Action a TC calls in one step
├── pub-check/                       # The acceptance criteria
│   ├── oasis_pub_check.py           #   170 individual checks in 58 classes, stdlib only
│   ├── CHECKS.md                    #   the acceptance criteria catalog, generated from the code
│   ├── AUTHORITIES.md               #   the criterion-to-clause map (verbatim OASIS policy)
│   ├── render_checks_md.py          #   the generator (keeps CHECKS.md in sync)
│   ├── manifest-schema.json         #   provenance manifest contract
│   ├── rules/                       #   oasis.rules.yaml, the criteria as data for nide
│   └── README.md                    #   checks, severities, corpus (canonical criteria)
├── PUBLICATION-QUALITY.md           # The TC-facing guide: both layers, all gates
├── examples/                        # Worked example + the regression corpus
│   ├── consumer-workflow.yml        #   the drop-in TC workflow (copy this)
│   ├── eox-core-v1.0-csd01/         #   the Validation Report from a publication
│   ├── csaf/                        #   archived CSAF work products (v2.0 lineage, v2.1 csd01)
│   └── csaf-cvrf/                   #   archived CSAF-CVRF v1.2 work products
├── tests/                           # The criteria's own regression suite (pytest)
│   ├── conftest.py                  #   loads the checker by path, copies corpus fixtures
│   ├── test_advertised_counts.py    #   the counts in the docs and diagrams vs the registry
│   ├── test_cli_smoke.py            #   the CLI contract: exit codes, --json, --list-checks
│   ├── test_delivery_items.py       #   delivery-item selection on a deployed tree
│   ├── test_manifest_emitter.py     #   Work Product Manifest File emitter
│   ├── test_markdown_renders.py     #   the shipped markdown renders as prose, not as HTML
│   ├── test_stage_uri_live.py       #   the live-URI probe: what blocks, what stays INFO
│   └── fixtures/                    #   hand-built defect trees (the corpus supplies the rest)
├── TRANSFORMS.md                    # The pipeline, command by command (canonical criteria)
├── assets/                          # The diagrams (PNG)
├── .github/
│   ├── src/                         # Pipeline source (pandoc + BeautifulSoup post-processing,
│   │                                #   HTML preprocessor, wkhtmltopdf renderer)
│   ├── scripts/                     # Shell entry points used by the workflows
│   ├── styles/                      # OASIS markdown-styles CSS lineage (v1.1 → v1.8.1)
│   └── workflows/                   # ci (this repo's own test suite), step_1 (MD→HTML),
│                                    #   step_2 (HTML→PDF), step_3 (zip), pub-check (the gate)
├── LICENSE                          # Apache-2.0 (software tier)
└── NOTICE                           # The three-tier IP statement
```

</details>

## Running the tests

The gate grades other people's publications, so a defect in it mis-grades work
silently. `tests/` is the regression net: a fixture per fixed defect, plus smoke
coverage over the CLI contract that `gate.py`, the composite action and the
publication runbook depend on.

The checker itself is stdlib-only. `pytest` is the one development dependency
and is not on the system Python, so use a venv:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install pytest
pytest tests/ -v                                    # the full suite
pytest tests/test_delivery_items.py -v              # one file
pytest tests/test_delivery_items.py::test_index_html_is_never_selected_as_the_delivery_item
```

The suite runs on every push and pull request
([`.github/workflows/ci.yml`](.github/workflows/ci.yml)), and a red run
blocks.

Fixtures come from the archived CSAF corpus under `examples/` wherever a
realistic package is needed. `tests/conftest.py` copies a corpus stage
directory into a `tmp_path` per test rather than duplicating multi-megabyte
artifacts under `tests/fixtures/`; the corpus is read, never modified.

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
