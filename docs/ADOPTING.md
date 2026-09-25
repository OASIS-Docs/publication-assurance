<!--
Copyright (c) OASIS Open 2026. All Rights Reserved.

This document may be copied, published, and distributed to others without
restriction, provided it is reproduced verbatim and this notice is retained.
Author: Michael Coletta, Technical Advisor to OASIS Open.
-->

# OASIS publication gate: adoption guide

This guide sets up `oasis-pub-check`, the OASIS publication acceptance tests,
in a TC's own GitHub repository. After setup, every push checks your
package against the same 173 conditions TC Administration runs at intake,
and each run publishes a Validation Report you can open in a browser.

| Section | Read it when |
|---|---|
| [Quick start](#quick-start) | You are setting the gate up for the first time |
| [The Validation Report](#the-validation-report) | A run has finished and you want to know what it says |
| [Blocker ownership](#blocker-ownership) | A blocker may not be the TC's to fix, or looks wrong |
| [Action inputs](#action-inputs) and [outputs](#action-outputs) | You want to change a default or use a result in a later step |
| [Markdown rendering before the gate](#markdown-rendering-before-the-gate) | Your repository holds Markdown sources, not a rendered package |
| [Gating and report-only runs](#gating-and-report-only-runs) | A blocker should not fail the build, for example on a published standard |
| [Several documents in one repository](#several-documents-in-one-repository) | The TC publishes more than one work product from this repository |
| [Fork pull requests and read-only tokens](#fork-pull-requests-and-read-only-tokens) | Contributors open pull requests from their own forks |
| [Version pinning and upgrades](#version-pinning-and-upgrades) | You want a newer release of the gate |
| [Local runs](#local-runs) | You want the verdict on your own machine before pushing |
| [Troubleshooting](#troubleshooting) | Something did not work as described |
| [Checks and their authorities](#checks-and-their-authorities) | You want the rule behind a finding |

| Term | Meaning |
|---|---|
| Workflow | A YAML file under `.github/workflows/` that tells GitHub Actions what to run and when |
| Run, job, step | One execution of a workflow; a job is a set of steps on one machine; a step is one command or action |
| Runner | The GitHub-hosted machine that runs a job |
| Job summary | The page of results a job writes, shown on the run's **Summary** page |
| Artifact | A file set attached to a run, downloadable from the bottom of the run's **Summary** page |
| Workflow token | The credential GitHub gives each run; `permissions:` sets what it may do |
| Matrix | One job definition run once per entry in a list, for example once per document |
| Exit code | The number a program ends with: `0` publishable, `1` blockers, `2` the target could not be read |

## Quick start

Three steps, about five minutes. You need write access to the TC
repository and the path of the package you want checked.

The package is a **stage directory**: the folder that holds one work
product at one stage, with its Markdown, HTML and PDF, for example
`work/v1.0/csd01` holding `mytc-v1.0-csd01.md`, `mytc-v1.0-csd01.html` and
`mytc-v1.0-csd01.pdf`. The gate checks two of the folder names against the
filenames and the cover URLs:

| Folder | Example | Rule |
|---|---|---|
| Stage directory | `csd01` | Named for the stage and revision |
| Its parent | `v1.0` | Named for the version |
| Anything above | `work/` | Your choice |

A `.zip` of the stage directory also works.

If the repository holds only Markdown and nothing renders it yet, finish
the Quick start with the path where the rendered package will go, then
read [Markdown rendering before the gate](#markdown-rendering-before-the-gate).

### Step 1: Workflow file

<!-- FINAL CHECK against validation-report-pdf: tag, inputs, permissions -->

1. In the TC repository, create the file `.github/workflows/pub-check.yml`
   with the content below. On GitHub: **Add file > Create new file**, and
   type the path into the name box.
2. Change the one line marked `EDIT` to the path of your package.
3. Commit the file to your default branch.

```yaml
name: pub-check

on:
  push:
  pull_request:
  workflow_dispatch:

permissions:
  contents: write   # lets the action publish the report to the pubcheck-reports branch

jobs:
  pub-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5

      - uses: OASIS-Docs/publication-assurance@v1.5.0
        with:
          target: work/v1.0/csd01   # EDIT: your stage directory or package .zip

      - uses: actions/upload-artifact@v7   # the report files, downloadable from the run page
        if: always()
        with:
          name: pubcheck-report
          path: pubcheck-report
          if-no-files-found: ignore
```

Committing the file starts the first run. In a private repository the run
uses the account's GitHub Actions minutes; public repositories run free.

**Success looks like:** the **Actions** tab lists a run named `pub-check`
for your commit. It finishes in about a minute. A green tick means the
package is publishable; a red cross means the gate found at least one
blocker. Either result means the setup works. A red cross with the
annotation `oasis-pub-check could not read the target` means the `target`
path is wrong: see [Troubleshooting](#troubleshooting).

### Step 2: Report page

<!-- FINAL CHECK against validation-report-pdf: branch name, folder layout, Pages URL -->

This step is optional and recommended. It gives every report a web
address that anyone can open without downloading anything.

The first run in Step 1 created a branch named `pubcheck-reports` that holds
the reports. If the **Branch** list in step 3 below does not offer it, that
run did not publish: see [Troubleshooting](#troubleshooting). To serve the
branch as a web page:

1. In the repository on GitHub, open **Settings > Pages**.
2. Under **Build and deployment**, set **Source** to **Deploy from a branch**.
3. Set **Branch** to `pubcheck-reports` and the folder to `/ (root)`, then
   select **Save**.

**Success looks like:** within a minute or two the Pages settings show
"Your site is live at `https://<owner>.github.io/<repo>/`". From the next
run on, the report links include an HTML page.

GitHub Pages is free for public repositories. A private repository needs a
paid GitHub plan for Pages; without it, skip this step and use the PDF and
Markdown links, which work in any repository.

### Step 3: First report

<!-- FINAL CHECK against validation-report-pdf: link labels, notice text, summary layout -->

1. Push any commit, or open **Actions > pub-check > Run workflow** and
   select **Run workflow**.
2. In the **Actions** tab, select the run. Its **Summary** page opens.
3. Scroll to the **pub-check** section of the summary. It starts with the
   report links: **PDF**, **Markdown**, **Folder** and, once Step 2 is
   done, **HTML**. The same links appear as a notice under
   **Annotations**, higher on the same page.
4. Open the report and read the verdict at the top.

| Result | Meaning | What to do |
|---|---|---|
| **PASS** | The condition was checked and met | Nothing |
| **WARN** | Publishable, recorded for the record; often a must-fix before a later stage | Read it; fix it or be ready to explain it |
| **BLOCKER** | The package cannot publish until this is fixed; the run fails | Fix it, or raise it with TC Administration if it is not the TC's to fix (see [Blocker ownership](#blocker-ownership)) |
| **NA** | The condition does not apply to this package; the report says why | Nothing, unless the reason is wrong for your package |
| **INFO** | Recorded, no action required | Nothing |

**Success looks like:** a report whose heading names your package and
whose verdict reads `PUBLICATION-READY: zero blockers.` or
`NOT publication-ready: N blocker(s).`. The run is red when the report
lists a blocker, or when no report could be produced (exit code `2`, a
wrong `target` path); your own package goes green once its blockers
are fixed. (The CSAF sample bundled with this repository stays red on one
blocker only staff can clear; see [Local runs](#local-runs).)

To fix a blocker, edit the source, commit, and push. The next run checks
the new commit and publishes a new report.

## The Validation Report

It is the report OASIS staff produce at intake, from the same code. It has
a header, a table of the 59 check classes and a table of all 173
conditions. The job summary shows the same two tables, above them the
findings list, which ends with the verdict in a second form,
`N blocker(s), M warning(s) -> NOT PUBLISHABLE`. The header lines described
below are in the report files.

### Verdict

The header block states the target, the date, the tool, the coverage
(173 conditions in 59 classes, all run), the blocker count and the gate's
exit code, then one **Result** line:

- `PUBLICATION-READY: zero blockers.` with exit code `0`. Warnings may remain.
- `NOT publication-ready: N blocker(s).` with exit code `1`.

Exit code `2` produces no report: the gate could not read the target,
almost always because the `target` path is wrong.

### Check class table

One row per check class, 59 rows, whether or not the class raised
anything. Each row gives the class result (PASS, or the most severe
finding in the class), the number of individual conditions inside the class, and up
to five findings in full. A class with more findings says how many more
and points at the JSON record, `pubcheck-report.json`, which lists all of
them.

Read this table first. Every row that is not PASS has a finding
beside it that says what was found and, where the check knows, where.

### Condition table

One row per condition, 173 rows. Each row gives:

| Column | Content |
|---|---|
| Result | PASS, WARN, BLOCKER, NA or INFO, with a count when one condition fired more than once (`WARN x10`) |
| Check | The check class the condition belongs to |
| Condition verified | What was tested, as one sentence |
| Value pulled (observed) | What the gate read from your package |
| Compared against | What it expected, often with the rule it comes from |

When a finding is not clear from the class table, find its row here: the
observed value and the expected value side by side usually show the fix.

### NA reasons

An NA row is a condition that does not apply, and its observed column
says why. The common reasons:

| NA reason | Meaning |
|---|---|
| `DOCX-render condition; this package carries no Word source` | The condition checks Word-authored packages only |
| `ODT-source condition; this package carries no ODT source` | The condition checks ODT-authored packages only |
| `evaluated on the markdown-source row for this package` | The same rule was checked against the Markdown, which is authoritative |
| `pdffonts unavailable or the package declares no font authority` | The runner had no poppler, or your HTML and CSS name no font family to compare against |
| `no manifest.json in the package` | Add a manifest to enable the manifest checks ([Local runs](#local-runs) shows `--emit-manifest`) |
| `not evaluated on this package: ...` | Something earlier in the same package stopped this condition from running; the rest of the text names it. Fix that and the condition runs. If the class it names shows PASS, report it to TC Administration |

A few conditions also need the network: they compare your package with
the live `docs.oasis-open.org`. GitHub's runners have network access, so
these run in CI.

### Blocker ownership

Almost every blocker is in the TC's own content, and the TC fixes it in
its source. A few concern things only OASIS staff can do or decide. Raise
those with TC Administration (a TCADMIN ticket, or
michael.coletta@oasis-open.org), quoting the finding. A finding you believe
is wrong goes to an issue on
[OASIS-Docs/publication-assurance](https://github.com/OASIS-Docs/publication-assurance/issues)
with the run link.

| Finding | Whose | Why |
|---|---|---|
| Naming, front matter, links, cited files, schemas `$id`, PDF out of step with the source, editor residue, required sections | TC | The fix is an edit to the TC's source |
| `member-uri`: a member-only (Kavi) URL is cited | TC, with staff help | The TC replaces the citation; staff can supply a public URL for the cited document |
| `public-review-metadata`: a reviewed stage lacks its public-review metadata file | TC Administration | Project Administration publishes that file (Naming Directives v1.7 s5.2) |
| `revision-collision` (WARN): the stage is already live | TC, with staff confirmation | A new submission takes the next revision number; ignore it when re-checking the published package itself |
| Any finding you believe is wrong | TC Administration | An issue on the repository, as above; false positives are fixed in the gate, not worked around in the document |

## Reference

### Action inputs

<!-- FINAL CHECK against validation-report-pdf: publishing inputs -->

All inputs except `target` are optional.

| Input | Default | Meaning |
|---|---|---|
| `target` | (required) | Stage directory or package `.zip`, relative to the repository root after checkout |
| `args` | `''` | Extra flags passed to the gate, for example `--emit-manifest`. `--json` is not needed: the action always writes `pubcheck-report.json`, and `--json` here turns `pubcheck-report.txt` into JSON too |
| `python-version` | `3.x` | Python version the gate runs on |
| `install-poppler` | `true` | Installs `pdftotext` and `pdffonts` on Linux runners for the PDF cross-checks. Without them those conditions report NA |
| `report-dir` | `pubcheck-report` | Where the report files are written in the job's working directory. `''` writes none |
| `write-summary` | `true` | Writes the verdict, the findings and the report tables to the job summary |
| `summary-title` | `''` (the target path is used) | Heading for this call's summary section; set it when the action runs more than once in a job or matrix |

### Action outputs

<!-- FINAL CHECK against validation-report-pdf: report-url-* and report-validation-pdf -->

Read an output in a later step as
`${{ steps.<step-id>.outputs.<name> }}`, which needs an `id:` on the gate
step.

| Output | Content |
|---|---|
| `exit-code` | `0` publishable, `1` blockers present, `2` target unreadable. This is what fails the step |
| `blockers` | Number of BLOCKER findings; empty when the exit code is `2` |
| `warnings` | Number of WARN findings; empty when the exit code is `2` |
| `report-txt` | Path to the plain-text findings list |
| `report-json` | Path to the full `--json` record |
| `report-validation-md` | Path to the Validation Report in Markdown |
| `report-validation-html` | Path to the Validation Report as one self-contained HTML page |
| `report-validation-pdf` | Path to the Validation Report as an A4 landscape PDF |
| `report-url-pdf` | Web address of the published PDF report |
| `report-url-md` | Web address of the published Markdown report |
| `report-url-folder` | Web address of the folder holding this run's reports |
| `report-url-html` | Web address of the HTML report on GitHub Pages, when Pages is on |

The path outputs are empty when `report-dir` is `''`; the three Validation
Report paths are also empty when that report could not be rendered, which
never changes the gate's result.

An example that posts the blocker count as a notice:

```yaml
      - id: gate
        uses: OASIS-Docs/publication-assurance@v1.5.0
        with:
          target: work/v1.0/csd01

      - if: always()
        env:
          BLOCKERS: ${{ steps.gate.outputs.blockers }}
          WARNINGS: ${{ steps.gate.outputs.warnings }}
        run: echo "::notice::pub-check found $BLOCKERS blocker(s) and $WARNINGS warning(s)"
```

`if: always()` matters: without it the step is skipped whenever the gate
fails.

### Markdown rendering before the gate

The gate checks a rendered package: the HTML and the PDF beside the
Markdown source, laid out at their `docs.oasis-open.org` path. If the
repository holds only Markdown, the workflow renders it first. The pattern
has three steps in one job:

1. **Render.** Markdown to HTML with the OASIS converter
   (`.github/src/step_1_markdown_to_html_converter_V3_0.py` in this
   repository), then HTML to PDF with the OASIS PDF preprocessor
   (`.github/src/fix_html_for_pdf.py`) and a headless browser.
2. **Stage.** Copy the Markdown, HTML, PDF, figures and schemas into a
   directory that mirrors the publish path, for example
   `_publication/lexidma/dmlex/v1.1/wd01/`. The path comes from the
   document's own "This stage" URL, so the directory, the filenames and the
   cover agree.
3. **Gate.** Point `target` at the staged directory.

[TRANSFORMS.md](../TRANSFORMS.md) gives every command of the pipeline.

**Worked example: DMLex.** The LexiDMA TC's DMLex Markdown editions run
this pattern. The files are
[`tools/publication-assurance/render.sh`](https://github.com/MColetta-OASIS/lexidma/tree/markdown-conversion/tools/publication-assurance)
(render and stage one edition, cloning this repository at a pinned
release) and the workflow
[`.github/workflows/publication-assurance.yml`](https://github.com/MColetta-OASIS/lexidma/blob/markdown-conversion/.github/workflows/publication-assurance.yml).
Condensed to one document (the DMLex workflow runs two, as a matrix), the
workflow is:

```yaml
name: pub-check

on:
  push:
  pull_request:
  workflow_dispatch:

permissions:
  contents: write

env:
  PANDOC_VERSION: 3.8.2.1
  PA_REF: v1.5.0          # the release render.sh clones

jobs:
  render-and-gate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5

      - name: Install pandoc and BeautifulSoup
        run: |
          curl -fsSL -o "$RUNNER_TEMP/pandoc.deb" \
            "https://github.com/jgm/pandoc/releases/download/${PANDOC_VERSION}/pandoc-${PANDOC_VERSION}-1-amd64.deb"
          sudo dpkg -i "$RUNNER_TEMP/pandoc.deb"
          python3 -m pip install --quiet beautifulsoup4

      - name: Render Markdown to HTML and PDF
        env:
          PUBCHECK: '0'           # render.sh stops after staging; the action gates
          CHROME: google-chrome   # preinstalled on GitHub's Ubuntu runners
        run: tools/publication-assurance/render.sh dmlex-v1.1 dmlex-v1.1/schemas _publication

      - name: OASIS publication gate
        uses: OASIS-Docs/publication-assurance@v1.5.0
        with:
          target: _publication/lexidma/dmlex/v1.1/wd01
```

Keep `PA_REF` and the action's tag on the same release, so the renderer and
the gate come from the same version.

### Gating and report-only runs

By default a blocker fails the step, the job and the run. That is the
right setting for a working draft. For a document that cannot change, such
as a published OASIS Standard kept in the repository for reference, add
`continue-on-error: true` to the gate step. The report is still written
and published, the step still shows its failure, and the job and the run
pass.

```yaml
      - uses: OASIS-Docs/publication-assurance@v1.5.0
        continue-on-error: true      # report only: findings never fail the job
        with:
          target: published/v1.0/os
```

In a matrix the setting can come from the matrix entry, as in the DMLex
workflow: `continue-on-error: ${{ !matrix.enforce }}`, with
`enforce: true` on the draft and `enforce: false` on the published
standard.

Warnings never fail a run in either mode.

### Several documents in one repository

Use a matrix, one entry per package. Each entry runs as its own job on its
own runner. Give each entry its own `summary-title`, so its summary is
headed with the document's name rather than its path, and its own artifact
name, because artifact names must be unique within a run.

```yaml
name: pub-check

on:
  push:
  pull_request:
  workflow_dispatch:

permissions:
  contents: write

jobs:
  pub-check:
    name: pub-check / ${{ matrix.package.name }}
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false        # one package's blocker does not cancel the others
      matrix:
        package:
          - id: core-v1.0-csd01
            name: Core v1.0 csd01
            target: work/core/v1.0/csd01
          - id: profile-v1.0-csd01
            name: Profile v1.0 csd01
            target: work/profile/v1.0/csd01
    steps:
      - uses: actions/checkout@v5

      - uses: OASIS-Docs/publication-assurance@v1.5.0
        with:
          target: ${{ matrix.package.target }}
          summary-title: ${{ matrix.package.name }}

      - uses: actions/upload-artifact@v7
        if: always()
        with:
          name: pubcheck-report-${{ matrix.package.id }}
          path: pubcheck-report
          if-no-files-found: ignore
```

`report-dir` matters only when one job calls the action more than once:
give each call its own, or the second call's files replace the first's.

[`examples/consumer-workflow-matrix.yml`](../examples/consumer-workflow-matrix.yml)
extends this with a manual override for a single target and a link to
each artifact in the job summary.

### Fork pull requests and read-only tokens

<!-- FINAL CHECK against validation-report-pdf: behaviour without write access -->

A pull request opened from a fork runs with a read-only token, whatever
the workflow's `permissions:` block says. GitHub does this so that code
from outside the repository cannot write to it. The gate itself needs no
write access and runs normally: the verdict, the red or green status, the
job summary and the report files on the runner are all produced. Only
publishing to the `pubcheck-reports` branch needs write access, so on a
fork pull request the report is not published and the run says so in a
warning; the gate result is unaffected.

The Quick start workflow's last step attaches the report files to the
run as an artifact whatever the token allows, so a fork's reports are
still available: they appear under **Artifacts** at the bottom of the run
page as `pubcheck-report`.

If the organisation or repository sets the default workflow token to
read-only (**Settings > Actions > General > Workflow permissions**), the
`permissions: contents: write` line in the workflow file overrides it for
this workflow. If an organisation policy forbids write tokens entirely,
the report is not published and the rest of the run is unchanged.

### Version pinning and upgrades

Pin the action to a full release tag, such as `@v1.5.0`. The releases,
with what each changed, are on the
[releases page](https://github.com/OASIS-Docs/publication-assurance/releases)
and in [CHANGELOG.md](../CHANGELOG.md).

| Reference | Behaviour |
|---|---|
| `@v1.5.0` | A fixed release. Recommended |
| `@<40-character commit SHA>` | Fixed and immune to a tag being moved. Use it where your organisation requires SHA pinning |
| `@v1` | Not recommended. This tag is not moved on each release and currently points to a build older than v1.4.0, without the Validation Report |
| `@main` | Unreleased code. Never for a TC workflow |

To find the SHA of a release:

```bash
git ls-remote https://github.com/OASIS-Docs/publication-assurance 'refs/tags/v1.5.0^{}'
```

To upgrade:

1. Read the new release's entry in the CHANGELOG. A MINOR release adds
   checks, so a package that passed may now show a new finding. A PATCH
   release fixes existing checks. A MAJOR release changes the exit codes,
   the `--json` shape or the action's contract.
2. Change the tag in the workflow file, and `PA_REF` too if the workflow
   renders Markdown.
3. Push, and compare the new report with the last one.

Dependabot can propose these upgrades as pull requests. Add
`.github/dependabot.yml`:

```yaml
version: 2
updates:
  - package-ecosystem: github-actions
    directory: /
    schedule:
      interval: weekly
```

### Local runs

The gate is one Python file with no dependencies beyond the standard
library, so it runs anywhere Python 3.10 or later does. The same code runs
in the action.

```bash
git clone --depth 1 --branch v1.5.0 https://github.com/OASIS-Docs/publication-assurance
python3 publication-assurance/pub-check/oasis_pub_check.py path/to/your/stage-dir
```

To try it before your own package is ready, point it at a package
bundled with the repository:

```bash
python3 publication-assurance/pub-check/oasis_pub_check.py publication-assurance/examples/csaf/v2.1/csd01
```

The last line is the verdict, for example
`1 blocker(s), 17 warning(s) -> NOT PUBLISHABLE`. That sample is the
published CSAF v2.1 CSD01, and its one blocker is `public-review-metadata`,
a file only OASIS staff can publish (see
[Blocker ownership](#blocker-ownership)); with the network checks off it
reports `0 blocker(s), 16 warning(s) -> publishable`. The exit status is the
same as the action's: `0`, `1` or `2`.

| Command | Result |
|---|---|
| `oasis_pub_check.py TARGET` | The findings list and the verdict |
| `oasis_pub_check.py TARGET --json` | The full machine-readable record: findings, every condition, and every observed value |
| `oasis_pub_check.py TARGET --emit-manifest` | Writes `manifest.json` and the `<stem>-manifest.txt` Work Product Manifest File into the stage directory, then checks it |
| `oasis_pub_check.py --list-checks` | Every check class with its condition count, derived from the code |
| `oasis_pub_check.py --help` | The options |
| `PUB_CHECK_OFFLINE=1 oasis_pub_check.py TARGET` | Skips the conditions that compare the package with the live `docs.oasis-open.org`; they report NA |

`--emit-manifest` writes into the stage directory, so run it on the
directory you intend to submit. The checks read the directory's own name
and path, so a renamed copy (such as `csd01-copy`) raises naming blockers
the real directory does not.

The Validation Report the action publishes can be rendered locally from
the `--json` record:

```bash
python3 publication-assurance/pub-check/oasis_pub_check.py path/to/your/stage-dir --json > report.json
code=$?
python3 publication-assurance/pub-check/validation_report.py report.json \
  --md report.md --html report.html --exit-code "$code"
```

Open `report.html` in a browser. If the first command exits `2` (the
target could not be read), `report.json` holds no report and the second
command has nothing to render: correct the path first.

The PDF conditions use `pdftotext` and `pdffonts` from poppler when they
are installed (`brew install poppler` on macOS,
`sudo apt-get install poppler-utils` on Debian and Ubuntu). Without them
those conditions report NA and the rest run unchanged.

### Troubleshooting

<!-- FINAL CHECK against validation-report-pdf: the report-publishing and HTML-link rows -->

| Symptom | Cause | Fix |
|---|---|---|
| Run fails with the annotation `oasis-pub-check could not read the target`, exit code 2, no report; the log says `... is not a directory` | `target` does not exist in the checked-out repository | Correct the path; it is relative to the repository root and case-sensitive on GitHub's runners |
| Run refused with "The job was not started because recent account payments have failed or your spending limit needs to be increased" | The account's Actions billing for a private repository: a failed payment, or the spending limit reached | The account owner fixes the payment or raises the spending limit, or the repository is made public |
| No run appears after committing the workflow | The file is not at `.github/workflows/`, or Actions is disabled | Check the path; enable Actions under **Settings > Actions > General** |
| `Unable to resolve action` | The tag in `uses:` does not exist | Use a tag from the [releases page](https://github.com/OASIS-Docs/publication-assurance/releases) |
| Job summary has the findings but no class or condition tables | The action is older than v1.5.0, often through `@v1` | Pin to `@v1.5.0` or later |
| Report publishing fails with a 403 or "permission denied" warning | The workflow token cannot write | Add `permissions: contents: write`; on a fork pull request this is expected, see [Fork pull requests](#fork-pull-requests-and-read-only-tokens) |
| The HTML link returns 404 | Pages is not on, or its first deployment has not finished | Complete [Step 2](#step-2-report-page); a new Pages site takes a minute or two |
| PDF conditions all NA with `pdffonts unavailable` | poppler is missing: `install-poppler: false`, or a macOS or Windows runner | Leave `install-poppler` at `true` and use `ubuntu-latest` |
| `public-review-metadata` blocker | The metadata file is published by Project Administration | Raise it with TC Administration; see [Blocker ownership](#blocker-ownership) |
| `revision-collision` warning | The stage you are checking is already live | Expected when re-checking a published package; a new submission takes the next revision number |
| Matrix summaries are headed with paths, not document names | `summary-title` is not set | Set `summary-title` per matrix entry |
| A matrix upload fails with `409` and "an artifact with this name already exists" | Two entries upload under one artifact name | Name each artifact from the matrix entry, as in [Several documents](#several-documents-in-one-repository) |
| Two calls to the action in one job leave only the second's report files | The calls share one `report-dir` | Give each call its own `report-dir` |
| Findings read `could not be reached ... (transport failure, not a 404)` | A network or site outage during the run | These are recorded as INFO, never as blockers. To skip the live-site conditions, set `env: PUB_CHECK_OFFLINE: '1'` on the gate step |
| A published standard in the repository keeps the run red | Its findings cannot be fixed in a published document | Run it report-only, see [Gating and report-only runs](#gating-and-report-only-runs) |
| A finding you believe is wrong | A gap or error in the gate | See [Blocker ownership](#blocker-ownership) |

### Checks and their authorities

| Document | Content |
|---|---|
| [pub-check/CHECKS.md](../pub-check/CHECKS.md) | Every condition: what is checked, the value pulled, what it is compared against, its severity, and when it applies. Generated from the code |
| [pub-check/AUTHORITIES.md](../pub-check/AUTHORITIES.md) | The OASIS rule behind each check, quoted verbatim with its source |
| [pub-check/README.md](../pub-check/README.md) | The check classes grouped by area, with severities and the regression corpus |
| [PUBLICATION-QUALITY.md](../PUBLICATION-QUALITY.md) | How the gate fits with the 15 audit gates TC Administration runs at intake |
| [TRANSFORMS.md](../TRANSFORMS.md) | The Markdown to HTML to PDF pipeline, command by command |
| [examples/eox-core-v1.0-csd01/](../examples/eox-core-v1.0-csd01/README.md) | A Validation Report from a real publication |
| [CHANGELOG.md](../CHANGELOG.md) | Every release, with the checks it added or changed |

Questions: michael.coletta@oasis-open.org. Findings you believe are
wrong: see [Blocker ownership](#blocker-ownership).
