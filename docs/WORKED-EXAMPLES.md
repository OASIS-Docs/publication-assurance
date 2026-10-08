<!--
Copyright (c) OASIS Open 2026. All Rights Reserved.
Author: Michael Coletta, Technical Advisor to OASIS Open.
-->

# Worked examples from recent publications

Each example below comes from a real OASIS work product checked between late
September and early October 2026. Each one gives the finding as the checks
printed it, what it meant, and the change that cleared it. Where the fault
was in the checks rather than the package, the example says so and names the
release that fixed it.

The finding text is quoted from the release named in each example, with long
lines wrapped and the end of a long message cut at `...`. Later releases may
word a message differently; [`pub-check/CHECKS.md`](../pub-check/CHECKS.md)
has the current conditions.

| Example | Work product | Check or tool | Fault in |
|---|---|---|---|
| [Table captions printed as raw Markdown](#table-captions-printed-as-raw-markdown) | CSAF v2.1 CSD03 | `html-residue`, `html-anchors` | The package |
| [Dual links and angle-bracket autolinks](#dual-links-and-angle-bracket-autolinks) | CSAF v2.1, working draft for CSD04 | `md-links` | The package; the advice in the checks |
| [Clauses reported as removed after a quote change](#clauses-reported-as-removed-after-a-quote-change) | CSAF v2.1, working draft for CSD04 | `conformance-structure` | The checks |
| [Code fences with text after the language](#code-fences-with-text-after-the-language) | CSAF v2.1 CSD03 | `fence-collapse` | The checks |
| [A PDF compared word for word with the published standard](#a-pdf-compared-word-for-word-with-the-published-standard) | DMLex v1.0 OS, Markdown edition | `verify_pdf.py` | The conversion |

## Table captions printed as raw Markdown

**Work product.** Common Security Advisory Framework Version 2.1 CSD03, as
published on docs.oasis-open.org. The package was checked again on
30 September 2026 with release v1.13.0.

**What the checks reported.** Ten blockers, in two classes. Five were
`html-residue` findings like this one:

```text
[BLOCKER] html-residue  Pandoc caption or attribute syntax is printed as text in
the HTML: 'Table: Remediation Combinations{#vulnerabilities-property-remediations-category-tab-1}'.
The renderer did not read it as a caption or an id, so readers see raw Markdown
and links to that id go nowhere. ...
```

The other five were `html-anchors` findings. Four were links to the missing
ids (`Internal link '#document-property-notes-tab-1' has no matching anchor
in the HTML.`). The fifth was a link with no `#` at all:

```text
[BLOCKER] html-anchors  Link href 'tab:tlp-labels-across-csaf-versions': 'tab:' is
not a web URL scheme, so a browser cannot follow the link. It reads as an internal
cross-reference written without its '#'. Its target's '{#tab:tlp-labels-across-csaf-versions}'
is printed as text, so that id is not set either: fix the caption, then write
href="#tab:tlp-labels-across-csaf-versions".
```

**What it meant.** All ten findings had one cause. At five tables the HTML
printed the caption as an ordinary paragraph ending in `{#id}`. The renderer
had not read that syntax, so the table ids were never set and every link to
them went nowhere. At four of the five, the published Markdown was already
written another way, with an anchor element before a plain caption line, so
the HTML had not been rendered from the Markdown that was published as the
authoritative source. At the fifth, the Markdown itself used the
pandoc-crossref form: a caption ending `{#tab:tlp-labels-across-csaf-versions}`
and a reference written `[tab](tab:tlp-labels-across-csaf-versions)`, which a
browser reads as a URL with the scheme `tab:`. A reader of the specification
had reported that link on the TC's issue tracker during the public review.

**The fix at source.** The TC traced the printed captions to its renderer:
the version of nide it had used did not handle tables with captions and
labels, and its working draft for CSD04 moved to a later release. The pandoc reader in the OASIS
pipeline's step 1 also reads the syntax, and turns
`Table: Remediation Combinations{#vulnerabilities-property-remediations-category-tab-1}`
into a `<table>` with that id and a caption. So the first fix is to render
the HTML from the published Markdown with a renderer that reads it, and to
check that each id appears in the HTML.

The `tab:` link needs a change to the Markdown itself. Link to the table's id
with `#`, as the message says:

```markdown
If the TLP label changes during such a conversion in a way not listed in
[the TLP label table](#tab:tlp-labels-across-csaf-versions), ...
```

The checks look at the HTML a reader gets, whatever produced it. On the
working draft at commit 73614d6, two blockers were left: the cross-reference
had its `#`, but the TLP table's caption still printed as text, so the link
still had no anchor to land on.

**Why earlier runs did not report all ten.** The `tab:` link and the printed
captions became conditions in v1.13.0, so earlier releases did not report
them. Two of the four dead `#` links were also dead in CSD02.

## Dual links and angle-bracket autolinks

**Work product.** CSAF v2.1: the published CSD03, and the TC's working draft
for CSD04.

**What the checks reported.** In CSD03, 13 warnings like this one (release
v1.13.0):

```text
[WARN   ] md-links      Dual link [url](url); prefer a bare URL (autolinked) or real
anchor text: https://docs.oasis-open.org/csaf/csaf/v2.1/schema/aggregator.json
```

**What it meant.** A link written `[https://example.org/x](https://example.org/x)`
repeats the URL as its own text. The check asks for one or the other. The
advice in v1.13.0 did not hold for every renderer. Whether a bare URL becomes
a link depends on the renderer: the OASIS pipeline's reader links bare URLs,
but in the CSAF PDF, which the TC renders with its own toolchain, a bare URL
is plain text. A TC editor who followed the advice could lose the link from
the PDF. One of the CSAF editors raised this on pull request 1635 in the
oasis-tcs/csaf repository.

**The fix at source.** Write the URL in angle brackets:

```markdown
<https://docs.oasis-open.org/csaf/csaf/v2.1/schema/aggregator.json>
```

This is Markdown's own autolink syntax, so it does not depend on whether a
renderer links bare URLs, and the check accepts it. Real
anchor text, `[the aggregator schema](https://...)`, is also accepted. From
v1.13.1 the warning recommends the angle-bracket form:

```text
[WARN   ] md-links      Dual link [url](url); write the URL in angle brackets,
<https://...>, which renders as a link in both the HTML and the PDF, or give it
real anchor text: https://...
```

The published CSD03 has 13 of these warnings. The TC's working draft for
CSD04 has none at commit 73614d6.

## Clauses reported as removed after a quote change

**Work product.** CSAF v2.1, the TC's working draft for CSD04, staged as
`csd04` and compared with the published CSD03.

**What the checks reported.** Six warnings, one per clause from 9.1.4 to
9.1.9 (release v1.13.0):

```text
[WARN   ] conformance-structure Clause number removed/renumbered (profile 'A
converter satisfies the “CSAF Converter” conformance profile if the converter:'):
'9.1.4' was present in the previous stage but is absent from this stage.
```

**What it meant.** Nothing had been removed. An editorial change (pull
request 1638 in oasis-tcs/csaf) had replaced the typographic quotes around
"CSAF Converter" in the profile's opening sentence with straight ones. The
checks identify a profile by its name, and the name now differed by two
characters, so every clause in the profile looked removed from the old one.

**The fix.** No change to the specification was needed. Release v1.13.1
folds curly quotes, apostrophes and Unicode dashes to their ASCII forms before
it compares profile names and clause text. On the same draft, at commit
73614d6, the six warnings went (11 warnings became 5) and nothing else
changed. A real removal, or a real wording change between a Committee
Specification and an OASIS Standard, is still reported.

**For TC editors.** A run of "removed" warnings that covers
every clause of one profile, after an edit that only touched punctuation,
points at the profile's name rather than its clauses. Check which release of
the checks the run used before changing the text.

## Code fences with text after the language

**Work product.** CSAF v2.1 CSD03.

**What the checks reported.** Before release v1.13.0, 96 `fence-collapse`
blockers. From v1.13.0, one warning that lists all 96 lines:

```text
[WARN   ] fence-collapse 96 code fence(s) carry trailing text in the info string
(Markdown lines 1368, 1481, 1509, ...). The published HTML shows each as a code
block, ...
```

**What it meant.** The CSAF source opens many code blocks with a fence such as
```` ```yaml <!--json-path($.properties)--> ````: a language followed by a comment.
Pandoc's GitHub-flavoured reader prints that as a code block. Its default
Markdown reader, which the OASIS pipeline's step 1 runs, collapses the block
to inline code. The checks used to assume the default reader and blocked
every such fence. CSAF does not render its HTML with step 1, and the
published HTML shows all 96 as code blocks, so the blockers were wrong. From
v1.13.0 the checks look at the HTML's `<pre>` blocks. A fence the HTML shows as code is
listed in one portability warning. A fence the HTML does not show as code is
still a blocker.

**The fix at source.** None is required while the TC renders its own HTML.
If the TC moves to the OASIS pipeline's step 1, these fences need another
form, because the default reader collapses them. The warning lists the line
of every fence that would change.

## A PDF compared word for word with the published standard

**Work product.** The Markdown edition of the Data Model for Lexicography
(DMLex) Version 1.0 OASIS Standard, converted from the published DocBook
source and rendered through the OASIS pipeline.

**What the tools reported.** The first renders passed every HTML comparison
(`verify/verify_md.py`) and a side-by-side look at the contents page.
`verify/verify_pdf.py`, which reads every word of both PDFs, found faults
the HTML comparison had passed, among them:

- 133 contents entries with no page numbers, where the published standard
  numbers all 171 of its entries. An HTML contents list has no page numbers,
  so no HTML comparison could see this;
- lettered lists printed `1.`, `2.`, `3.`, where the standard prints `a.`,
  `b.`, `c.` and its text refers to "point c. above";
- appendix contents one level too shallow: 38 entries under A.2.2 and F.1.2
  were missing from the contents.

**What it meant.** The words of the edition matched the standard. Its
contents page numbers, list numbering and appendix contents did not. Since
v1.10.0, `verify_md.py` also compares list numbering and the contents entry
by entry, but only the PDF comparison sees page numbers.

**The fix at source.** All three were fixed in the conversion and the
pipeline, not by editing the rendered PDF. The pipeline's step 2 numbers the
contents from the printed pages. The converter numbers nested lists the way
the DocBook stylesheet does, and lists appendix contents one level deeper.
The DMLex profile records the differences that are accepted, with a reason for
each, in
[`allow-pdf.json`](../converters/docbook-to-markdown/profiles/dmlex/allow-pdf.json).
Some of those are defects of the published PDF itself: its font has no `ň`
or `ō`, so it prints `#` for them 15 times.

**How the page review was checked.** A person or a model still has to look at
the pages, for a figure off the page or a caption beside the wrong block.
`render/review_pairs.py make` pairs rendered and published pages and plants
one fault the reviewer is not told about. `grade` rejects a pair when fewer
than four in five of the lines the reviewer copied are on its pages, and
accepts the review only when every pair passes and the planted fault is named
for what it is.
On DMLex one model copied lines that are not on the page for 21 of 36 pairs
and missed the planted fault, so its review was rejected. Another named the
fault, and was accepted after five pairs were reviewed again. [`render/README.md`](../render/README.md) and
[`verify/README.md`](../verify/README.md) give the commands.

---

**The documentation set:** [Repository overview](../README.md) · [TC guide](../PUBLICATION-QUALITY.md) · [Adoption guide](ADOPTING.md) · [The criteria catalog](../pub-check/CHECKS.md) · [Convert and verify](CONVERT-AND-VERIFY.md)
