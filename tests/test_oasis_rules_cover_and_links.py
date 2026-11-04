# Copyright 2026 OASIS Open
# SPDX-License-Identifier: Apache-2.0
# Authored by Michael Coletta, Technical Advisor to OASIS Open.
"""oasis.rules.yaml: the cover, keyword, Notices and link-text rules.

Eight rules carry the cover-page completeness, keyword and IPR-notice areas of
the TC Handbook's editorial quality verification checklist, and the markdown
half of link-mismatch, into the file nide reads (Nov 2026). CI does not
install nide, so the rules are applied here by a small evaluator that follows
nide's own semantics for the four check types they use (nide/_quality.py:
section-present searches each heading, any-match and all-match search each
prose line outside code fences, conditional is not applicable when its
condition fails). Where nide is installed, the last test runs nide's own
engine over the same documents and asserts the two agree.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

from conftest import CORPUS, oasis_pub_check

RULES_FILE = Path(oasis_pub_check.__file__).parent / "rules" / "oasis.rules.yaml"
RULES = {r["id"]: r for r in yaml.safe_load(RULES_FILE.read_text(encoding="utf-8"))["rules"]}

NEW = ["OASIS-COVER-THIS-STAGE", "OASIS-COVER-PREVIOUS-STAGE", "OASIS-COVER-LATEST-STAGE",
       "OASIS-TITLE-VERSION", "OASIS-COVER-STAGE", "OASIS-NOTICES",
       "OASIS-KEYWORDS-SECTION", "OASIS-LINK-TEXT-MISMATCH"]

# Published Markdown that passes every one of the new rules.
CSAF_CSD01 = CORPUS / "csaf" / "v2.1" / "csd01" / "csaf-v2.1-csd01.md"
CSAF_OS = CORPUS / "csaf" / "v2.0" / "os" / "csaf-v2.0-os.md"


def _split(md: str) -> tuple[list[str], list[str]]:
    headings, prose, fence = [], [], None
    for line in md.split("\n"):
        m = re.match(r"\s*(`{3,}|~{3,})", line)
        if m:
            if fence is None:
                fence = m.group(1)[0]
            elif line.strip() == m.group(1) and m.group(1)[0] == fence:
                fence = None
            continue
        if fence is not None:
            continue
        h = re.match(r"#{1,6} +(.*)$", line)
        (headings if h else prose).append(h.group(1) if h else line)
    return headings, prose


def _pattern(check: dict) -> re.Pattern:
    return re.compile(check["pattern"], re.I if check.get("flags") == "IGNORECASE" else 0)


def evaluate(check: dict, md: str) -> str:
    headings, prose = _split(md)
    t = check["type"]
    if t == "section-present":
        return "PASS" if any(_pattern(check).search(h) for h in headings) else "FAIL"
    assert check.get("target", "prose") == "prose", check
    if t == "any-match":
        return "PASS" if any(_pattern(check).search(x) for x in prose) else "FAIL"
    if t == "all-match":
        hits = [x for x in prose if _pattern(check).search(x)]
        return "FAIL" if (hits if check.get("invert") else len(hits) != len(prose)) else "PASS"
    if t == "conditional":
        if evaluate(check["condition"], md) != "PASS":
            return "NA"
        return evaluate(check["then"], md)
    raise AssertionError(f"check type {t!r} not covered by this evaluator")


def result(rule_id: str, md: str) -> str:
    return evaluate(RULES[rule_id]["check"], md)


def test_the_new_rules_are_in_the_file_with_their_severities():
    assert {i: RULES[i]["severity"] for i in NEW} == {
        "OASIS-COVER-THIS-STAGE": "BLOCKER", "OASIS-COVER-PREVIOUS-STAGE": "BLOCKER",
        "OASIS-COVER-LATEST-STAGE": "BLOCKER", "OASIS-TITLE-VERSION": "WARN",
        "OASIS-COVER-STAGE": "WARN", "OASIS-NOTICES": "WARN",
        "OASIS-KEYWORDS-SECTION": "WARN", "OASIS-LINK-TEXT-MISMATCH": "WARN"}
    for i in NEW:
        assert "TC Handbook, Editorial quality verification checklist" in RULES[i]["description"], i


@pytest.mark.parametrize("rule_id, label", [
    ("OASIS-COVER-THIS-STAGE", "This stage/version"),
    ("OASIS-COVER-PREVIOUS-STAGE", "Previous stage/version"),
    ("OASIS-COVER-LATEST-STAGE", "Latest stage/version"),
])
def test_the_cover_rules_use_pub_checks_expressions(rule_id, label):
    pat = next(p for lbl, p, _req in oasis_pub_check.TEMPLATE_SECTIONS if lbl == label)
    check = RULES[rule_id]["check"]
    assert check["pattern"] == "^" + pat
    assert check["flags"] == "IGNORECASE"


@pytest.mark.parametrize("path", [CSAF_CSD01, CSAF_OS], ids=lambda p: p.name)
def test_a_published_document_passes_every_new_rule(path):
    md = path.read_text(encoding="utf-8")
    assert len(md) > 100_000  # the real document, not a stub
    assert {i: result(i, md) for i in NEW} == {i: "PASS" for i in NEW}


# Heading wordings measured across the published Markdown (CSAF, DPS, NIEMOpen,
# OData, AMQP, SARIF) and the Word-native covers (KMIP, PKCS#11, LegalDocML,
# ECF): every one must satisfy its rule.
WORDINGS = {
    "OASIS-COVER-THIS-STAGE": ["This stage", "This stage:", "This version", "This Version:"],
    "OASIS-COVER-PREVIOUS-STAGE": ["Previous stage:", "Previous version", "Previous Version:"],
    "OASIS-COVER-LATEST-STAGE": ["Latest stage<a id='latest-stage'></a>", "Latest version:"],
    "OASIS-TITLE-VERSION": ["Common Security Advisory Framework Version 2.1",
                            "OData Version 4.02. Part 1: Protocol", "NIEM Model Version 6.0"],
    "OASIS-COVER-STAGE": ["Committee Specification Draft 02", "Committee Specification 01",
                          "Committee Note 01", "Committee Note Draft 01", "OASIS Standard",
                          "Candidate OASIS Standard 01", "OASIS Approved Errata",
                          "Project Specification Draft 01", "Project Note 01"],
    "OASIS-NOTICES": ["Notices", "License, Document Status, and Notices", "Appendix C. Notices"],
}


@pytest.mark.parametrize("rule_id, heading",
                         [(r, h) for r, hs in WORDINGS.items() for h in hs])
def test_each_template_wording_satisfies_its_rule(rule_id, heading):
    assert result(rule_id, f"# {heading}\n\nText.\n") == "PASS"


@pytest.mark.parametrize("rule_id, heading", [
    ("OASIS-COVER-THIS-STAGE", "What this version adds"),
    ("OASIS-COVER-LATEST-STAGE", "Changes since the latest version"),
    ("OASIS-TITLE-VERSION", "Changes From the Previous Version"),
    ("OASIS-COVER-STAGE", "Committee Specification process"),
])
def test_a_body_heading_that_only_mentions_the_words_does_not_pass(rule_id, heading):
    assert result(rule_id, f"# {heading}\n\nText.\n") == "FAIL"


def test_keywords_section_applies_only_where_key_words_are_used():
    assert result("OASIS-KEYWORDS-SECTION", "# Intro\n\nThe client may retry.\n") == "NA"
    assert result("OASIS-KEYWORDS-SECTION", "# Intro\n\nThe client MUST retry.\n") == "FAIL"
    for heading in ("Key Words", "Key words:", "Keywords", "1.2 Terminology"):
        md = f"# {heading}\n\nBCP 14 applies.\n\n# Intro\n\nThe client MUST retry.\n"
        assert result("OASIS-KEYWORDS-SECTION", md) == "PASS", heading


def _pub_check_link_mismatches(md: str) -> int:
    f = oasis_pub_check.Findings()
    oasis_pub_check.check_correction_classes(md, "", "", "csd01", f)
    return sum(1 for x in f.items if x["check"] == "link-mismatch")


LINKS = {
    "same URL": "[https://a.example/x](https://a.example/x)",
    "trailing slash on the target": "[https://a.example/x](https://a.example/x/)",
    "trailing slash on the text": "[https://a.example/x/](https://a.example/x)",
    "both slashed": "[https://a.example/x/](https://a.example/x/)",
    "the prov-meta rename": ("[https://docs.oasis-open.org/dps/prov-meta/v1.0/csd02/prov-meta-v1.0-csd02.md]"
                             "(https://docs.oasis-open.org/dps/prov-meta/v1.0/csd01/prov-meta-v1.0-csd02.md)"),
    "target is longer": "[https://a.example/x](https://a.example/xy)",
    "target is shorter": "[https://a.example/xy](https://a.example/x)",
    "a fragment on the target": "[https://a.example/x](https://a.example/x#s)",
    "http against https": "[http://a.example/x](https://a.example/x)",
    "text that is not a URL": "[the spec](https://a.example/x)",
    "two links, the second wrong": "[https://a.example/x](https://a.example/x) and [https://b.example/](https://c.example/)",
}


@pytest.mark.parametrize("line", LINKS.values(), ids=LINKS.keys())
def test_link_text_rule_agrees_with_pub_check(line):
    want = "FAIL" if _pub_check_link_mismatches(line) else "PASS"
    assert result("OASIS-LINK-TEXT-MISMATCH", line + "\n") == want


def test_link_text_rule_is_case_sensitive_like_pub_check():
    assert "flags" not in RULES["OASIS-LINK-TEXT-MISMATCH"]["check"]


# One mutation per rule on a copy of the passing CSAF document: remove what the
# rule looks for, prove the copy changed, and watch the rule fail.
MUTATIONS = {
    "OASIS-COVER-THIS-STAGE": (r"(?m)^#+ This stage.*$", ""),
    "OASIS-COVER-PREVIOUS-STAGE": (r"(?m)^#+ Previous stage.*$", ""),
    "OASIS-COVER-LATEST-STAGE": (r"(?m)^#+ Latest stage.*$", ""),
    # Every heading naming a version goes: the title is the one a cover carries,
    # and the rule cannot tell it from a body heading.
    "OASIS-TITLE-VERSION": (r"(?m)^(#+ .*?)\bVersion\s+\d", r"\1Release "),
    "OASIS-COVER-STAGE": (r"(?m)^#+ Committee Specification Draft 01.*$", ""),
    "OASIS-NOTICES": (r"(?m)^(#+ )Notices", r"\1Legal"),
    # The whole line, or the heading's own anchor id "terminology" still matches.
    "OASIS-KEYWORDS-SECTION": (r"(?m)^(#+ [\d.]*\s*)Terminology.*$", r"\1Words used"),
    "OASIS-LINK-TEXT-MISMATCH": (r"\]\(https://docs\.oasis-open\.org/csaf/csaf/v2\.1/schema/csaf\.json\)",
                                 "](https://docs.oasis-open.org/csaf/csaf/v2.1/csd01/schema/csaf.json)"),
}


@pytest.mark.parametrize("rule_id", NEW)
def test_each_rule_fails_when_its_target_is_removed(rule_id):
    md = CSAF_CSD01.read_text(encoding="utf-8")
    pat, repl = MUTATIONS[rule_id]
    mutated = re.sub(pat, repl, md)
    assert mutated != md, "mutation did not apply"
    assert result(rule_id, md) == "PASS"
    assert result(rule_id, mutated) == "FAIL"


def test_nide_itself_agrees_with_this_evaluator():
    nide_quality = pytest.importorskip("nide._quality")
    from nide._config import Config
    from nide._ir import AssemblyIR, BodyNode, HeadingNode

    def ir(md: str) -> AssemblyIR:
        nodes, fence = [], None
        for line in md.split("\n"):
            m = re.match(r"\s*(`{3,}|~{3,})", line)
            h = re.match(r"(#{1,6}) +(.*)$", line) if fence is None and not m else None
            if m:
                fence = m.group(1)[0] if fence is None else None
            if h:
                nodes.append(HeadingNode(tag=h.group(1) + " ", text=h.group(2), label="",
                                         sec_cnt_disp="", display_key="", level=len(h.group(1)),
                                         is_in_special=False, has_explicit_prefix=False))
            else:
                nodes.append(BodyNode(text=line + "\n"))
        return AssemblyIR("2.0", nodes, [], [], {}, {}, {}, {})

    rules, ctx = nide_quality.load_ruleset([RULES_FILE])
    md = CSAF_CSD01.read_text(encoding="utf-8")
    docs = [md] + [re.sub(MUTATIONS[i][0], MUTATIONS[i][1], md) for i in NEW]
    for doc in docs:
        got = {f.rule_id: f.result for f in nide_quality.run_quality(rules, ctx, ir(doc), Config())}
        assert {i: got[i] for i in NEW} == {i: result(i, doc) for i in NEW}
