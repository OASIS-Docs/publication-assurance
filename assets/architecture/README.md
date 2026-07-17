# Publication quality architecture diagrams

Hand-authored, self-contained SVGs (shapes and text only, no scripts, no
external references). Both diagrams, and every other SVG under `assets/`,
regenerate from one build script and one set of design tokens, the OASIS TC
Handbook visual system: Poppins with Helvetica/Arial fallback, ink `#0a2540`,
accent `#2248e5`, hairline borders, 2px radii. Each SVG has a companion PNG
rendered at 2x.

```bash
python3 ../build.py          # rewrites all six SVGs from assets/
python3 ../build.py --png    # also renders the 2x PNGs (needs rsvg-convert)
```

## Subject

How the OASIS publication quality architecture's two layers dovetail:

- **Layer 1, validation (pub-check):** mechanical, tool-side. `pub_check.py`,
  92 checks across 34 check classes. The TC runs it in its own CI before
  submission, and TC Administration re-runs the identical code at intake. It
  only ever sees the package files. Output: the Validation Report, every one
  of the 92 conditions with the observed value the tool pulled set against
  the expected value it was compared to, never truncated (rendered landscape
  so the full values stay legible).
- **Layer 2, the publication audit:** human and adversarial, event-side. 15
  mandatory gates run against live ground truth the tool cannot see: byte
  identity, render class vs precedent, live roster, Naming Directives, index
  chain, zip integrity, four announcement channels, ticket record, an
  independent adversarial verifier, a literal visual eyeball. Every gate
  needs recorded evidence; the verdict is computed from the record, not
  asserted. Output: the Publication Audit Report.
- **The dovetail:** intake checklist step 4b requires running pub-check and
  triaging every finding, so the whole 92-check validation layer plugs into
  the audit as one step. Both reports are filed to the TC's ticket and the
  internal `_audit/` directory.

The prose companion to these diagrams is
[../../PUBLICATION-QUALITY.md](../../PUBLICATION-QUALITY.md).

## Files

### `validation-audit-dovetail.svg` (1400 x 900, landscape), flagship

Two swim lanes, TC side (Layer 1) and TC Administration side (Layer 2). The
shared `pub-check` engine sits in the seam between them with dovetail keys
seating into both lanes: the identical code running on both sides, the TC in
CI on the left, checklist step 4b on the right. The audit gates that need
live ground truth are laid out as a chip grid, the independent adversarial
verifier is called out separately, and both report artifacts flow down to
the shared TCADMIN ticket and `_audit/` record. Primary explainer figure for
TC editors and for TC Administration process documentation.

### `two-layer-stack.svg` (900 x 1100, portrait), slide summary

A vertical stack that reads bottom to top: package in, Layer 1 validation,
the step-4b dovetail joint, Layer 2 audit, published and verified
publication. Each layer carries a "what the tool sees" (Layer 1) versus
"what only a human or live check can see" (Layer 2) annotation panel. One
slide in a deck, or a sidebar summary next to the flagship diagram.
