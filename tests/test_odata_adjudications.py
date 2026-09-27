# Copyright 2026 OASIS Open
# SPDX-License-Identifier: Apache-2.0
# Authored by Michael Coletta, Technical Advisor to OASIS Open.
"""Two blockers TC Administration ruled gate false positives on the OData
v4.02 csd02 packages (TCADMIN-4733/4734/4735/4737, 27 Aug 2026), found still
raised by the current gate when harvest/harvest.py re-ran the recorded
packages (proposal 013, 27 Sep 2026).

- template: OData writes its Conformance heading with an anchor inside it,
  `# <a id="Conformance" href="#Conformance">17 Conformance</a>`, and the
  gate read that as no Conformance section.
- filenames: a multi-part work product names its parts
  [WP-abbrev]-[version-id]-[stage][rev]-[partNumber]-[partName]
  (Naming Directives v1.7), and the gate demanded the stem end in the stage.
"""

from __future__ import annotations

from conftest import oasis_pub_check


def _template(md):
    f = oasis_pub_check.Findings()
    oasis_pub_check.check_template(md, "", f)
    return [x["message"] for x in f.items if x["check"] == "template" and "Conformance" in x["message"]]


def test_an_anchor_wrapped_conformance_heading_is_a_conformance_section():
    assert _template('# <a id="Conformance" href="#Conformance">17 Conformance</a>\n\ntext\n') == []
    assert _template("## 2 Conformance\n") == []
    assert _template("# 1 Introduction\n\nNo such section.\n") != []


def _stem_findings(stem):
    f = oasis_pub_check.Findings()
    items = {ext: f"/x/{stem}.{ext}" for ext in ("md", "html", "pdf")}
    oasis_pub_check.check_filenames(items, "csd02", f, required=("md", "html", "pdf"))
    return [x["message"] for x in f.items if x["check"] == "filenames" and "does not end in" in x["message"]]


def test_a_multi_part_stem_ends_in_its_part_not_its_stage():
    assert _stem_findings("odata-v4.02-csd02-part1-protocol") == []
    assert _stem_findings("odata-v4.02-csd02-part2-url-conventions") == []
    assert _stem_findings("odata-v4.02-csd01-part1-protocol") != []
    assert _stem_findings("odata-v4.02-csd02-draft") != []
