# Copyright 2026 OASIS Open
# SPDX-License-Identifier: Apache-2.0
# Authored by Michael Coletta, Technical Advisor to OASIS Open.
"""Output names each rule by its published document, never by a corpus file.

The checker's messages and its condition registry cite the snapshot files it
was built from ("per handbook-Conformance.txt", "naming-directives.txt Section
4"). Those names exist only in pub-check/corpus/. A chair reading a validation
report cannot look up "handbook-Conformance.txt"; he can look up the TC
Handbook page "Conformance Clauses" (CSAF v2.1 csd04 report, Oct 2026).

The rewrite happens at output, so the check code and the condition signatures
keep their corpus names and nothing that matches on them moves.
"""

from __future__ import annotations

import json
import re

import pytest

from conftest import CORPUS, REPO_ROOT, oasis_pub_check, run_cli, stage_from_corpus

MANIFEST = REPO_ROOT / "pub-check" / "corpus" / "MANIFEST.json"
CORPUS_FILES = sorted(d["text_file"] for d in
                      json.loads(MANIFEST.read_text())["documents"].values())
CORPUS_NAME_RE = re.compile(r"(?<![\w-])(?:" + "|".join(map(re.escape, CORPUS_FILES)) + r")\b")


def test_every_corpus_document_has_a_public_name():
    names = oasis_pub_check.public_rule_names()
    assert sorted(names) == CORPUS_FILES
    for corpus_file, title in names.items():
        assert title and ".txt" not in title and ".html" not in title, (corpus_file, title)


@pytest.mark.parametrize("raw, expected", [
    ("label it 'Non-normative' per handbook-Conformance.txt.",
     "label it 'Non-normative' per the TC Handbook page 'Conformance Clauses'."),
    ("valid stage prefixes (naming-directives.txt Section 4)",
     "valid stage prefixes (the OASIS Naming Directives v1.7 Section 4)"),
    ("concluded (tc-process.txt s2.7: the downstream approval ballot",
     "concluded (the OASIS Technical Committee (TC) Process s2.7: the downstream approval ballot"),
    ("a stale stage. handbook-PublicReviews.txt: the three cover page URIs",
     "a stale stage. The TC Handbook page 'Public Review': the three cover page URIs"),
])
def test_a_corpus_file_name_is_replaced_by_the_document_name(raw, expected):
    assert oasis_pub_check.cite_publicly(raw) == expected


def test_text_that_cites_no_corpus_file_is_unchanged():
    s = "write the two release manifests, manifest.json and csaf-v2.1-csd01-manifest.txt"
    assert oasis_pub_check.cite_publicly(s) == s


@pytest.fixture(scope="module")
def json_run(tmp_path_factory):
    stage = stage_from_corpus(tmp_path_factory.mktemp("corpus"), CORPUS / "csaf" / "v2.1" / "csd01")
    result = run_cli("--json", str(stage))
    assert result.returncode in (0, 1), result.stderr
    return json.loads(result.stdout)


def test_the_registry_itself_still_cites_corpus_files():
    """Precondition: without it the next test could pass on a registry that
    simply stopped citing anything."""
    raw = json.dumps(oasis_pub_check.conditions_inventory())
    assert CORPUS_NAME_RE.search(raw)


def test_json_output_names_no_corpus_file(json_run):
    leaks = sorted({m.group(0) for m in CORPUS_NAME_RE.finditer(json.dumps(json_run))})
    assert leaks == []
    assert "TC Handbook page" in json.dumps(json_run["conditions"])
