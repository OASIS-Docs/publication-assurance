# Copyright 2026 OASIS Open
# SPDX-License-Identifier: Apache-2.0
# Authored by Michael Coletta, Technical Advisor to OASIS Open.
"""render/review_pairs.py: page pairs for a vision review, and its grading.

The grader is the point. On the DMLex pairs (Sep 2026) a Haiku reviewer
"copied" lines about NVH nodes from the contents page, and its planted-fault
pair carried a difference that had nothing to do with the fault; a grader
that counted any difference as a catch accepted it. A review passes only
when its copied lines are on the pages they claim, and the planted fault is
named for what it is.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys

import pytest

from conftest import REPO_ROOT
from test_verify_pdf import document, printed

PAIRS = REPO_ROOT / "render" / "review_pairs.py"

pytestmark = pytest.mark.skipif(not (shutil.which("pdftoppm") and shutil.which("pdfimages")),
                                reason="poppler (pdftoppm, pdfimages) is not installed")


def run(*args):
    return subprocess.run([sys.executable, str(PAIRS), *map(str, args)], capture_output=True, text=True)


@pytest.fixture
def made(tmp_path):
    pytest.importorskip("PIL")
    pub = printed(tmp_path, "pub", document(split=2))
    ren = printed(tmp_path, "ren", document(split=6))
    out, key = tmp_path / "pairs", tmp_path / "key.json"
    r = run("make", ren, pub, out, "--key", key, "--sample", 1, "--seed", 3, "--plant", "right-column")
    assert r.returncode == 0, r.stderr
    return json.loads(key.read_text(encoding="utf-8")), out, key, pub, ren


def page_lines(pdf, n):
    text = subprocess.run(["pdftotext", "-layout", "-f", str(n), "-l", str(n), str(pdf), "-"],
                          capture_output=True, text=True).stdout
    lines = [x.strip() for x in text.splitlines() if len(x.strip()) >= 8]
    return (lines * 5)[:5]


def honest(k, pub, ren, planted_says="the page numbers of the contents are missing on the right"):
    review = []
    for p in k["pairs"]:
        review.append({"pair": p["pair"], "left_lines": page_lines(pub, p["published_page"]),
                       "right_lines": page_lines(ren, p["rendered_page"]), "only_left": [], "only_right": [],
                       "differences": [planted_says] if p["pair"] == k["planted_pair"] else []})
    return review


def grade(tmp_path, key, review):
    path = tmp_path / "review.json"
    path.write_text(json.dumps(review), encoding="utf-8")
    return run("grade", key, path)


def test_make_writes_one_image_per_pair_and_the_brief(made):
    k, out, _, _, _ = made
    assert len(k["pairs"]) == len(list(out.glob("pair-*.png"))) >= 3
    assert sum("planted" in p for p in k["pairs"]) == 1 and k["planted"] == "right-column"
    rendered = [p["rendered_page"] for p in k["pairs"]]
    assert len(rendered) == len(set(rendered)), "the planted page must not also appear untouched"
    brief = (out / "PROMPT.md").read_text(encoding="utf-8")
    assert all(p["pair"] in brief for p in k["pairs"]) and "Copy the first" in brief
    assert "planted" not in brief.lower() and k["planted_pair"] not in (out / "PROMPT.md").read_text().split("pairs:")[0]


def test_the_key_may_not_sit_where_the_reviewer_reads(tmp_path, made):
    _, out, _, pub, ren = made
    r = run("make", ren, pub, out, "--key", out / "key.json")
    assert r.returncode != 0 and "outside" in r.stderr


def test_an_honest_review_that_names_the_fault_is_accepted(tmp_path, made):
    k, _, key, pub, ren = made
    r = grade(tmp_path, key, honest(k, pub, ren))
    assert r.returncode == 0, r.stdout
    assert "FOUND" in r.stdout and "ACCEPTED" in r.stdout


def test_lines_not_on_the_page_are_rejected(tmp_path, made):
    k, _, key, pub, ren = made
    review = honest(k, pub, ren)
    review[0]["left_lines"] = ["NVH node: collocate implements the collocationMarker",
                               "Child nodes are optional and zero or more", "lemma OPTIONAL zero or one",
                               "label OPTIONAL zero or more entries", "REQUIRED implements the text property"]
    r = grade(tmp_path, key, review)
    assert r.returncode == 1 and "not copied from the page" in r.stdout


def test_a_difference_that_does_not_name_the_fault_is_a_miss(tmp_path, made):
    k, _, key, pub, ren = made
    r = grade(tmp_path, key, honest(k, pub, ren, planted_says="the left shows generic text, the right specific"))
    assert r.returncode == 1 and "MISSED" in r.stdout


def test_an_unanswered_pair_or_too_few_lines_is_incomplete(tmp_path, made):
    k, _, key, pub, ren = made
    review = honest(k, pub, ren)
    review[-1]["right_lines"] = review[-1]["right_lines"][:2]
    r = grade(tmp_path, key, review[1:] if review[0]["pair"] != k["planted_pair"] else review[:1] + review[2:])
    assert r.returncode == 1 and "not answered" in r.stdout
    r = grade(tmp_path, key, review)
    assert r.returncode == 1 and "fewer than 5" in r.stdout


def test_a_re_run_of_the_rejected_pairs_completes_the_review(tmp_path, made):
    k, _, key, pub, ren = made
    good = honest(k, pub, ren)
    bad = [dict(x) for x in good]
    bad[0]["left_lines"] = ["lines copied from some other page entirely"] * 5
    (tmp_path / "first.json").write_text(json.dumps(bad), encoding="utf-8")
    (tmp_path / "rerun.json").write_text(json.dumps(good[:1]), encoding="utf-8")
    assert run("grade", key, tmp_path / "first.json").returncode == 1
    r = run("grade", key, tmp_path / "first.json", tmp_path / "rerun.json")
    assert r.returncode == 0, r.stdout
