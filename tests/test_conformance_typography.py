# Copyright 2026 OASIS Open
# SPDX-License-Identifier: Apache-2.0
# Authored by Michael Coletta, Technical Advisor to OASIS Open.
"""conformance-structure: straightening a quote does not remove a clause.

The stability diff keys every clause on (profile name, clause number), and
the profile name is taken from the sentence that names it. oasis-tcs/csaf
PR #1638 changed the curly quotes around "CSAF Converter" in one profile
sentence to straight ones, so the previous stage's key no longer matched and
clauses 9.1.4 to 9.1.9 were each reported as removed: six false WARNs (CSAF
branch head 73614d6, Oct 2026). Quotes, apostrophes and dashes are now folded
to ASCII before profile names and clause text are compared.
"""

from __future__ import annotations

import pytest

from conftest import oasis_pub_check

PREV_URL = "https://docs.oasis-open.org/wid/wid/v1.0/csd01/wid-v1.0-csd01.md"
FRONT = (f"# Widget Version 1.0\n\n#### This stage\n"
         f"https://docs.oasis-open.org/wid/wid/v1.0/csd02/wid-v1.0-csd02.md\n\n"
         f"#### Previous stage\n{PREV_URL}\n\n#### Latest stage\n"
         f"https://docs.oasis-open.org/wid/wid/v1.0/wid-v1.0.md\n\n#### Abstract\nText.\n\n")
BODY = ("# 1 Introduction\n\nText.\n\n# 2 Conformance\n\n## 2.1 Conformance Targets\n\n"
        "### 2.1.1 Conformance Clause 1: Widget Converter\n\n"
        "A converter satisfies the {q}Widget Converter{q2} conformance profile if the converter:\n\n"
        "* reads the input{dash}all of it.\n\n"
        "### 2.1.2 Conformance Clause 2: Widget Converter output\n\n"
        "* writes the converter{apos}s output.\n\n"
        "# Appendix A. Acknowledgments\n\nThanks.\n")

# Curly double quotes, an en dash and a curly apostrophe, against ASCII.
CURLY = BODY.format(q="“", q2="”", dash="–", apos="’")
STRAIGHT = BODY.format(q='"', q2='"', dash="-", apos="'")


def stability_warnings(prev_md, cur_md, monkeypatch, tmp_path):
    monkeypatch.setattr(oasis_pub_check, "_resolve_previous_stage_artifact",
                        lambda stage_dir, url: ("csd01", prev_md, False))
    f = oasis_pub_check.Findings()
    oasis_pub_check.check_conformance_structure(cur_md, "", str(tmp_path), "csd02", f)
    assert f.observed["conformance-structure"]["previous_stage_resolved"] == "True"
    return [x["message"] for x in f.items if x["check"] == "conformance-structure"
            and ("removed/renumbered" in x["message"] or "silently renumbered" in x["message"])]


@pytest.mark.parametrize("prev, cur", [(CURLY, STRAIGHT), (STRAIGHT, CURLY)],
                         ids=["curly-to-straight", "straight-to-curly"])
def test_a_typographic_change_does_not_report_clauses_removed(prev, cur, monkeypatch, tmp_path):
    assert stability_warnings(FRONT + prev, FRONT + cur, monkeypatch, tmp_path) == []


def test_a_typographic_change_is_not_a_wording_change_at_cs_to_os(monkeypatch, tmp_path):
    """At CS -> OS the clause text is compared by hash, so the same fold
    applies there: a straightened apostrophe or dash is not reworded text."""
    monkeypatch.setattr(oasis_pub_check, "_resolve_previous_stage_artifact",
                        lambda stage_dir, url: ("cs01", FRONT + CURLY, False))
    f = oasis_pub_check.Findings()
    oasis_pub_check.check_conformance_structure(FRONT + STRAIGHT, "", str(tmp_path), "os", f)
    assert f.observed["conformance-structure"]["cs_to_os_transition"] == "True"
    assert [x["message"] for x in f.items if "wording differs" in x["message"]
            or "numbering differs" in x["message"]] == []


def test_a_real_wording_change_at_cs_to_os_is_still_reported(monkeypatch, tmp_path):
    reworded = STRAIGHT.replace("reads the input", "parses the input")
    monkeypatch.setattr(oasis_pub_check, "_resolve_previous_stage_artifact",
                        lambda stage_dir, url: ("cs01", FRONT + CURLY, False))
    f = oasis_pub_check.Findings()
    oasis_pub_check.check_conformance_structure(FRONT + reworded, "", str(tmp_path), "os", f)
    got = [x["message"] for x in f.items if "wording differs" in x["message"]]
    assert len(got) == 1 and "(2.1.1)" in got[0], got


def test_a_clause_really_removed_is_still_reported(monkeypatch, tmp_path):
    """The fold must not hide a real removal."""
    cut = STRAIGHT[:STRAIGHT.index("### 2.1.2")] + "# Appendix A. Acknowledgments\n\nThanks.\n"
    got = stability_warnings(FRONT + CURLY, FRONT + cut, monkeypatch, tmp_path)
    assert len(got) == 1 and "'2.1.2'" in got[0] and "removed/renumbered" in got[0], got
