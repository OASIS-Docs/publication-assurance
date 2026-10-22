# Copyright 2026 OASIS Open
# SPDX-License-Identifier: Apache-2.0
# Authored by Michael Coletta, Technical Advisor to OASIS Open.
"""pdf-sync: another version cited in Related work is not a stale-draft tell.

pdf-sync warns when the PDF's first pages cite a different version of the
same specification, because a PDF rendered from an older draft carries the
older version's addresses. The markdown front-matter check has always
excused the Previous stage and Related work blocks, where citing another
version is the point; pdf-sync excused nothing. CSAF v2.1 csd04 (22 Oct 2026)
lists CSAF v2.0 under "This specification replaces or supersedes:" and got a
pdf-sync WARN for it, which the TC chair rightly asked about.

The OASIS templates do not word that sentence the same way: the CS 1.05 and
CN 1.01 markdown templates say "This document replaces or supersedes:", the
V4.1 HTML template "This specification replaces or supercedes:", CSAF and
NIEM "This specification replaces or supersedes:". The "Related Work" heading
is the same in all of them, so it is the primary anchor and the sentence the
fallback. The block ends at the next front-matter label; with none in reach,
nothing is excused.

CSD04_PAGE2 is the CSAF v2.1 csd04 PDF's own text (pdftotext -l 3), cut to
the lines that matter, including the Latest-stage URL wrapped at "https://".
"""

from __future__ import annotations

import types

from conftest import oasis_pub_check

BASE = "https://docs.oasis-open.org/csaf/csaf/v2.1/csd04/"
VERSION = "v2.1"

COVER = f"""Common Security Advisory Framework Version 2.1
Committee Specification Draft 04
21 October 2026
This stage
{BASE}csaf-v2.1-csd04.md (Authoritative)
Previous stage
https://docs.oasis-open.org/csaf/csaf/v2.1/csd03/csaf-v2.1-csd03.md (Authoritative)
Latest stage
https://docs.oasis-open.org/csaf/csaf/v2.1/csaf-v2.1.md (Authoritative)
Technical Committee
OASIS Common Security Advisory Framework (CSAF) TC
"""

CSD04_PAGE2 = """Standards Track Work Product
Related work
This specification replaces or supersedes:
• Common Security Advisory Framework Version 2.0. Edited by Langley Rock, Stefan Hagen, and Thomas Schmidt. 18
November 2022. OASIS Standard. https://docs.oasis-open.org/csaf/csaf/v2.0/os/csaf-v2.0-os.html. Latest stage: https://
docs.oasis-open.org/csaf/csaf/v2.0/csaf-v2.0.html.
Declared JSON namespaces:
• https://docs.oasis-open.org/csaf/csaf/v2.1/schema/aggregator.json
Abstract
The Common Security Advisory Framework (CSAF) Version 2.1 is the definitive reference for the language which supports
"""

V20 = "https://docs.oasis-open.org/csaf/csaf/v2.0/os/csaf-v2.0-os.html"


def version_warnings(monkeypatch, text):
    monkeypatch.setattr(oasis_pub_check.shutil, "which", lambda _: "/usr/bin/pdftotext")
    monkeypatch.setattr(oasis_pub_check.subprocess, "run",
                        lambda *a, **k: types.SimpleNamespace(stdout=text, stderr="", returncode=0))
    f = oasis_pub_check.Findings()
    oasis_pub_check.check_pdf("x.pdf", BASE, VERSION, f)
    return f, [x["message"] for x in f.items
               if x["check"] == "pdf-sync" and "previous-stage reference" in x["message"]]


def test_csd04_superseded_version_in_related_work_is_not_warned(monkeypatch):
    f, warns = version_warnings(monkeypatch, COVER + CSD04_PAGE2)
    assert warns == []
    # the excused citation is still shown as evidence on the passing row
    assert "v2.0" in f.observed["pdf-sync"]["other_versions_excused"]


def test_template_105_wording_without_a_heading_is_excused(monkeypatch):
    page = ("This document replaces or supersedes:\n"
            f"• CSAF Version 2.0. OASIS Standard. {V20}.\n"
            "This document is related to:\n"
            "• https://docs.oasis-open.org/csaf/csaf/v1.9/csaf-v1.9.html\n"
            "License, Document Status, and Notices\n")
    _f, warns = version_warnings(monkeypatch, COVER + page)
    assert warns == []


def test_v41_template_misspelling_is_excused(monkeypatch):
    page = ("Related Work:\nThis specification replaces or supercedes:\n"
            f"{V20}\nAbstract:\n")
    _f, warns = version_warnings(monkeypatch, COVER + page)
    assert warns == []


def test_another_version_outside_the_block_still_warns(monkeypatch):
    # the same URL after the block has closed (Declared namespaces) is a stale-draft tell
    page = CSD04_PAGE2.replace("aggregator.json", f"aggregator.json\n• {V20}")
    _f, warns = version_warnings(monkeypatch, COVER + page)
    assert len(warns) == 1 and "/v2.0/" in warns[0]


def test_another_version_on_the_cover_still_warns(monkeypatch):
    cover = COVER.replace("csaf/v2.1/csd03/csaf-v2.1-csd03.md",
                          "csaf/v2.0/csd03/csaf-v2.0-csd03.md").replace(
        "Latest stage\n", f"Latest stage\n{V20}\n")
    _f, warns = version_warnings(monkeypatch, cover + CSD04_PAGE2)
    assert len(warns) == 1 and "/v2.0/" in warns[0]


def test_an_unterminated_related_work_block_excuses_nothing(monkeypatch):
    # no front-matter label closes the block within reach: fail closed
    page = "Related work\nThis specification replaces or supersedes:\n" + f"{V20}\n" + "body text\n" * 80
    _f, warns = version_warnings(monkeypatch, COVER + page)
    assert len(warns) == 1


def test_a_url_wrapped_at_the_scheme_is_still_read(monkeypatch):
    # pdftotext breaks long URLs after "https://"; the wrapped half used to escape the scan
    page = ("Notes\nSee https://\ndocs.oasis-open.org/csaf/csaf/v1.7/csaf-v1.7.html for history.\n")
    _f, warns = version_warnings(monkeypatch, COVER + page)
    assert len(warns) == 1 and "/v1.7/" in warns[0]
