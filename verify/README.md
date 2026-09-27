<!--
Copyright 2026 OASIS Open
SPDX-License-Identifier: Apache-2.0
Authored by Michael Coletta, Technical Advisor to OASIS Open.
-->

# verify_md: a Markdown edition against the published HTML

`verify_md.py` answers one question: does this Markdown file say exactly what
the published HTML of the same specification says? Use it when a TC converts
an existing specification (DocBook, Word) to the OASIS Markdown template and
has to show the conversion changed nothing.

Requirements: Python 3.10 or later (standard library only) and pandoc 3.x.
Older pandoc releases parse GitHub Flavored Markdown differently and produce
differences that are not in the document; the tool refuses them and records
the version it used in the report.

```bash
python3 verify/verify_md.py SPEC.md PUBLISHED [--root DIR] [--allow FILE] [--json OUT] [--strict]
```

| Argument | Meaning |
|---|---|
| `SPEC.md` | The Markdown edition |
| `PUBLISHED` | The published HTML: a saved file or an `https://docs.oasis-open.org/...` URL |
| `--root DIR` | Where the Markdown's image paths are resolved (default: the Markdown's directory) |
| `--allow FILE` | Accepted deviations, each with a reason (below) |
| `--json OUT` | The full report, every difference in full |
| `--strict` | Also fail when an allow rule accepted nothing |

Exit `0` when every check passes, `1` when any fails, `2` when an input
cannot be read (a missing file, no pandoc, an allow rule without a reason).
The last line printed is `RESULT: PASS` or `RESULT: FAIL`.

## What it checks

| Check | Passes when |
|---|---|
| Words | Every published word appears in the Markdown in the same order, and nothing is added, apart from the allowed deviations. Both sides are reduced to visible text and aligned with `difflib`; tables of contents are left out of both. |
| Headings | Every numbered published heading is in the Markdown, in order |
| Code blocks | Same number of `<pre>` blocks, each identical in order (whitespace at line ends ignored) |
| Lists and tables | Same number of list items; same data tables (two or more rows) with the same row and cell counts |
| Internal links | Every `#id` link in the Markdown has an anchor |
| Images | Every image the Markdown references exists under `--root`, and the counts match |
| Not empty | Neither side is empty |

`docs.oasis-open.org` is served through Cloudflare, which replaces each email
address with `[email protected]` and an encoded attribute. The verifier
decodes them, so a live URL and a saved copy give the same result.

## Reading the output

Each unexplained difference prints as

```
[replace] ...the words just before it
  PUB: the published words
  MD : the Markdown words
```

`replace` means the words changed, `delete` that the Markdown dropped them,
`insert` that it added them. Accepted deviations print as `ACCEPTED:` lines
with their reason, and a rule that matched nothing prints as
`UNUSED ALLOW RULE:`.

## The allow file

Some differences are intended: the OASIS Markdown template labels the stage
URLs "This stage" where an older DocBook edition said "This version", and the
HTML page footer is not document content. Each is written down once, with the
reason a reader can check:

```json
[
 {"published": "version", "markdown": "stage", "count": 3, "reason": "Naming Directives v1.7 labels"},
 {"published": ":", "markdown": "", "context": "Notices", "reason": "'Notices:' label rendered as a heading"},
 {"kind": "heading", "published": "F.1.2.1 csd04.xmlTracking of ...", "reason": "source defect"}
]
```

`published` and `markdown` are the token strings the report prints, matched
exactly. A rule accepts one difference unless it gives `count`, and with
`context` only a difference whose preceding words end with that text. Any
difference no rule accepts fails the run, so the allow file is the complete,
reviewable list of every way the Markdown differs from the publication.

The DMLex rules are in
[`converters/docbook-to-markdown/profiles/dmlex/allow.json`](../converters/docbook-to-markdown/profiles/dmlex/allow.json).
With them, the DMLex v1.0 OASIS Standard Markdown edition matches
<https://docs.oasis-open.org/lexidma/dmlex/v1.0/os/dmlex-v1.0-os.html> on
61,258 words, 311 headings, 316 code blocks, 1,133 list items and 50 images
(`tests/test_verify_md.py`).

## What it does not check

Styling, page layout and the rendered PDF. Those are the gate's job
(`pub-check/`) and the pipeline's.
