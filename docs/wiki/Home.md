<!--
Copyright 2026 OASIS Open
SPDX-License-Identifier: Apache-2.0
Authored by Michael Coletta, Technical Advisor to OASIS Open.
-->

# OASIS publication checks

Before a TC specification is published to `docs.oasis-open.org`, OASIS runs
it through the publication acceptance checks (`oasis-pub-check`). This wiki
is the reading guide to those checks for TC editors and chairs. Run the
checks in your own repository before your TC votes, and fix what they find
while the document is still yours to change.

Every page here is generated from the markdown in the
[publication-assurance repository](https://github.com/OASIS-Docs/publication-assurance), so it matches the
current code on `main`.

## Adopt the checks in a TC repository

- [Adoption guide](../ADOPTING.md): the three-step quick start, with the
  workflow file to copy.
- [Several documents in one repository](../ADOPTING.md#several-documents-in-one-repository),
  [fork pull requests](../ADOPTING.md#fork-pull-requests-and-read-only-tokens)
  and [version pinning](../ADOPTING.md#version-pinning-and-upgrades).
- [Local runs](../ADOPTING.md#local-runs): the same checks on your own machine.

## Read a check result

- [What a committee sees](../ADOPTING.md#what-a-committee-sees): the job
  summary, the pull request comment and the line annotations.
- [The Validation Report](../ADOPTING.md#the-validation-report): the verdict,
  the check class table and the condition table.
- [Example Validation Report](../../examples/eox-core-v1.0-csd01/README.md)
  from a live publication.

## Fix a finding

- [Worked examples](../WORKED-EXAMPLES.md): recent findings, each with the
  message, what it meant and the fix at source.
- [Troubleshooting](../ADOPTING.md#troubleshooting) for the workflow itself.

## Look up a check or rule

- [Check catalog](../../pub-check/CHECKS.md): every check, generated from the code.
- [Policy authorities](../../pub-check/AUTHORITIES.md): the OASIS rule behind
  each check, quoted with its source.
- [Source-text rules](../../pub-check/rules/README.md): the rules file that
  authoring tools read.
- [The checker](../../pub-check/README.md): what each check class covers,
  severities, and how a check is changed.

## Convert and verify a document

- [Convert and verify](../CONVERT-AND-VERIFY.md): one workflow that converts,
  renders, verifies and checks a specification.
- [Markdown edition](../MARKDOWN-EDITION.md) of a DocBook specification.
- [Markdown pipeline](../../TRANSFORMS.md), command by command.
- [Rendering](../../render/README.md), [verifying a conversion](../../verify/README.md)
  and the [DocBook to Markdown converter](../../converters/docbook-to-markdown/README.md).

## Background

- [Publication quality](../../PUBLICATION-QUALITY.md): how OASIS validates and
  audits a specification, in two layers.
- [Repository overview](../../README.md) and the [changelog](../../CHANGELOG.md).
