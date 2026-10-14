# Copyright 2026 OASIS Open
# SPDX-License-Identifier: Apache-2.0
# Authored by Michael Coletta, Technical Advisor to OASIS Open.
"""pdf-cover: the Citation format block is not a second title block.

The check counts the title on page 1 to catch a duplicated title block (DPS,
May 2026). SARIF v2.2 csd01's Typst layout fits the template's Citation format
block on page 1, and the citation names the title ("<title>. Edited by ..."),
so a correct cover reported the title twice. The page-1 text below is the
SARIF PDF's own (pdftotext -l 1), cut to the lines that matter.
"""

from __future__ import annotations

import types

import pytest

from conftest import oasis_pub_check

TITLE = "Static Analysis Results Interchange Format (SARIF) Version 2.2"

SARIF_PAGE1 = f"""Standards Track Work Product

{TITLE}
Committee Specification Draft 01
09 October 2026
Technical Committee
OASIS Static Analysis Results Interchange Format (SARIF) TC
Abstract:
This document defines a standard format for the output of static analysis tools. The format is referred to as the “Static
Analysis Results Interchange Format” and is abbreviated as SARIF.
Citation format:
When referencing this specification, the following citation format should be used:
[SARIF-v2.2]
Static Analysis Results Interchange Format (SARIF) Version 2.2. Edited by Michael Fanning and Stefan Hagen. 09 Octo­
ber 2026. Committees Specification Draft. https://docs.oasis-open.org/sarif/sarif/v2.2/csd01/sarif-v2.2-csd01.html.
"""


def cover_blockers(monkeypatch, page1):
    monkeypatch.setattr(oasis_pub_check.shutil, "which", lambda _: "/usr/bin/pdftotext")
    monkeypatch.setattr(oasis_pub_check.subprocess, "run",
                        lambda *a, **k: types.SimpleNamespace(stdout=page1))
    f = oasis_pub_check.Findings()
    oasis_pub_check.check_pdf_cover("cover.pdf", TITLE, f)
    return [x["message"] for x in f.items if x["check"] == "pdf-cover"]


def test_the_citation_naming_the_title_is_not_residue(monkeypatch):
    assert cover_blockers(monkeypatch, SARIF_PAGE1) == []


@pytest.mark.parametrize("citation", ["_{t}_. Edited by A. Editor.", "“{t}.” Edited by A. Editor."])
def test_a_citation_in_emphasis_or_quotes_is_not_residue(monkeypatch, citation):
    page1 = f"{TITLE}\nCitation format:\n" + citation.format(t=TITLE)
    assert cover_blockers(monkeypatch, page1) == []


def test_a_second_title_block_still_blocks_beside_the_citation(monkeypatch):
    page1 = f"{TITLE}\n{TITLE}\nCommittee Specification Draft 01\n" + SARIF_PAGE1
    got = cover_blockers(monkeypatch, page1)
    assert len(got) == 1 and "appears 3 times" in got[0], got
