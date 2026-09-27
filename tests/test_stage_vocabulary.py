# Copyright 2026 OASIS Open
# SPDX-License-Identifier: Apache-2.0
# Authored by Michael Coletta, Technical Advisor to OASIS Open.
"""Every stage token the gate accepts has a written source (proposal 010).

VALID_STAGE_PREFIXES carried wd, ps, psd, pn and pnd with no citation, and
advance_stage.py imports the set. Naming Directives v1.7 lists csd, cs, os,
errata, cnd and cn; it mentions wd only as an unpublished working-draft
pattern. The Open Project stages are published (NIEMOpen ps01, psd01, pn01,
pnd01 under docs.oasis-open.org/niemopen) with no clause in the pinned corpus.
"""

from __future__ import annotations

import re

from conftest import REPO_ROOT, oasis_pub_check

CORPUS = REPO_ROOT / "pub-check" / "corpus"


def _norm(t):
    return re.sub(r"\s+", " ", t).strip()


def test_every_accepted_token_has_a_source():
    assert set(oasis_pub_check.STAGE_TOKEN_SOURCES) == oasis_pub_check.VALID_STAGE_PREFIXES


def test_every_corpus_source_is_verbatim():
    for token, (source, quote) in oasis_pub_check.STAGE_TOKEN_SOURCES.items():
        if source == "published":
            assert quote.startswith("https://docs.oasis-open.org/"), token
            continue
        text = _norm((CORPUS / source).read_text(encoding="utf-8"))
        assert _norm(quote) in text, f"{token}: {quote!r} is not in {source}"


def _stage(token):
    f = oasis_pub_check.Findings()
    oasis_pub_check.check_stage_name(token, f)
    return [(x["severity"], x["message"]) for x in f.items if x["check"] == "stage-name"]


def test_a_working_draft_warns_that_it_is_not_published():
    got = _stage("wd01")
    assert [s for s, _ in got] == ["WARN"] and "Working Draft" in got[0][1]


def test_published_open_project_and_committee_stages_pass():
    for token in ("csd01", "cs02", "os", "cnd01", "cn01", "psd01", "ps01", "pnd01", "pn01"):
        assert _stage(token) == [], token
