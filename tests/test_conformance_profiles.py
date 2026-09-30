# Copyright 2026 OASIS Open
# SPDX-License-Identifier: Apache-2.0
# Authored by Michael Coletta, Technical Advisor to OASIS Open.
"""conformance-structure: each profile is judged on its own clauses.

CSAF names each conformance profile in a sentence under the clause heading:

    ### 9.1.36 Conformance Clause 36: CSAF Extension Collection
    A set of artifacts satisfies the "CSAF Extension Collection" conformance profile if it:

The profile scope began at that sentence, so every clause heading was
credited to the profile before it and the last profile was always reported
as having no clauses (CSAF v2.1 csd03, Sep 2026). A profile sentence directly
under its clause heading now begins at the heading.
"""

from __future__ import annotations

from conftest import oasis_pub_check

HEAD = "# 1 Introduction\n\nText.\n\n# 2 Scope\n\nText.\n\n# 3 Conformance\n\n## 3.1 Conformance Targets\n\n"
CLAUSES = (
    '### 3.1.1 Conformance Clause 1: Widget\n\n'
    'A file satisfies the "Widget" conformance profile if it:\n\n* is a widget.\n\n'
    '### 3.1.2 Conformance Clause 2: Gadget\n\n'
    'A program satisfies the "Gadget" conformance profile if it:\n\n* makes widgets.\n\n')
TAIL = "# Appendix A. Acknowledgments\n\nThanks.\n"


def findings(md, tmp_path):
    f = oasis_pub_check.Findings()
    oasis_pub_check.check_conformance_structure(md, "", str(tmp_path), "csd01", f)
    return f


def test_the_last_profile_is_credited_with_its_own_clause(tmp_path):
    f = findings(HEAD + CLAUSES + TAIL, tmp_path)
    assert [x["message"] for x in f.items if "not populated" in x["message"]] == []
    assert f.observed["conformance-structure"]["profiles_found"] == "2"
    assert f.observed["conformance-structure"]["clauses_extracted"] == "2"


def test_a_profile_with_no_clause_heading_is_still_reported(tmp_path):
    """The fix must not hide a real gap: a third profile sentence with no
    clause heading of its own draws the WARN."""
    extra = 'Finally, a doohickey satisfies the "Doohickey" conformance profile if it:\n\n* exists.\n\n'
    f = findings(HEAD + CLAUSES + extra + TAIL, tmp_path)
    got = [x for x in f.items if "not populated" in x["message"]]
    assert len(got) == 1 and "Doohickey" in got[0]["message"]


def test_profiles_named_by_their_own_headings_keep_their_scopes(tmp_path):
    """'## 3.2 Core Profile' style: the profile is a heading, and the clause
    before it stays with the previous profile."""
    md = (HEAD.replace("## 3.1 Conformance Targets\n\n", "")
          + "## 3.1 Core Profile\n\n### 3.1.1 Clause A\n\nText.\n\n"
          + "## 3.2 Extended Profile\n\n### 3.2.1 Clause B\n\nText.\n\n" + TAIL)
    f = findings(md, tmp_path)
    assert [x for x in f.items if "not populated" in x["message"]] == []
    scopes = oasis_pub_check._split_profiles(md[md.index("# 3 Conformance"):md.index("# Appendix")])
    assert "3.1.1 Clause A" in scopes["Core Profile"] and "3.2.1" not in scopes["Core Profile"]
    assert "3.2.1 Clause B" in scopes["Extended Profile"] and "3.1.1" not in scopes["Extended Profile"]
