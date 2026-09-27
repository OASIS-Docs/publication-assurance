# Copyright 2026 OASIS Open
# SPDX-License-Identifier: Apache-2.0
# Authored by Michael Coletta, Technical Advisor to OASIS Open.
"""The pipeline's step 1 HTML says what the published standard says.

verify_md.py reads the Markdown with pandoc's GFM reader; the pipeline's
step 1 renders it with pandoc's markdown reader and its own transforms, and
that HTML is what is published. Verifying the step 1 output of the DMLex
v1.0 OS edition against the published page found step 1 expanding the tabs
in 9 of the 316 code blocks (fixed: --preserve-tabs), and the verifier
reading step 1's <h1big> title as an <h1> that swallowed the cover (fixed).
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys

import pytest

from conftest import FIXTURES, REPO_ROOT

VERIFY = REPO_ROOT / "verify" / "verify_md.py"
STEP1 = REPO_ROOT / ".github" / "src" / "step_1_markdown_to_html_converter_V3_0.py"
EDITION = FIXTURES / "verify_md" / "dmlex-v1.0-os"
PUBLISHED = EDITION / "published-dmlex-v1.0-os.html"
PROFILE = REPO_ROOT / "converters" / "docbook-to-markdown" / "profiles" / "dmlex"

pytestmark = pytest.mark.skipif(
    shutil.which("pandoc") is None and not os.environ.get("REQUIRE_PANDOC"),
    reason="pandoc is not installed (CI sets REQUIRE_PANDOC=1)")


@pytest.fixture(scope="module")
def step1_html(tmp_path_factory):
    out = tmp_path_factory.mktemp("s1")
    stage = out / "lexidma" / "dmlex" / "v1.0" / "os"
    shutil.copytree(EDITION, stage, ignore=shutil.ignore_patterns("published-*"))
    r = subprocess.run([sys.executable, str(STEP1), str(stage / "dmlex-v1.0-os.md"), str(out), str(stage),
                        "--md-to-html"], cwd=stage, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]
    return stage


def verify(stage, *extra):
    return subprocess.run([sys.executable, str(VERIFY), str(stage / "dmlex-v1.0-os.md"), str(PUBLISHED),
                           "--rendered", str(stage / "dmlex-v1.0-os.html"), "--allow", str(PROFILE / "allow.json"),
                           *extra], capture_output=True, text=True)


def test_the_step1_html_matches_the_published_standard(step1_html):
    r = verify(step1_html, "--allow", str(PROFILE / "allow-rendered.json"))
    assert r.returncode == 0, r.stdout[-4000:] + r.stderr
    assert "code_blocks_differing: (0, [])" in r.stdout and "code_blocks_markdown: 316" in r.stdout
    assert "headings_missing: (0, [])" in r.stdout


def test_step1_keeps_tabs_in_code_blocks(step1_html):
    html = (step1_html / "dmlex-v1.0-os.html").read_text(encoding="utf-8")
    assert "\n\t\t\thint: navigate" in html


def test_without_the_rendered_allow_rules_the_logo_is_reported(step1_html):
    r = verify(step1_html)
    assert r.returncode == 1 and "images/OASISLogo-v3.0.png" in r.stdout


def _pair(tmp_path, md, rendered, published):
    (tmp_path / "x-v1.0-csd01.md").write_text(md, encoding="utf-8")
    (tmp_path / "r.html").write_text(rendered, encoding="utf-8")
    (tmp_path / "p.html").write_text(published, encoding="utf-8")
    return subprocess.run([sys.executable, str(VERIFY), str(tmp_path / "x-v1.0-csd01.md"), str(tmp_path / "p.html"),
                           "--rendered", str(tmp_path / "r.html")], capture_output=True, text=True)


MD = "This stage: https://docs.oasis-open.org/w/x/v1.0/csd01/x-v1.0-csd01.html\n"


def test_a_custom_title_tag_is_not_read_as_a_heading(tmp_path):
    r = _pair(tmp_path, MD, "<h1big>Title</h1big><h2>1 Scope</h2><p>Wait...</p><h1>2 Next</h1>",
              "<h1>Title</h1><h2>1 Scope</h2><p>Wait…</p><h1>2 Next</h1>")
    assert "headings_missing: (0, [])" in r.stdout and r.returncode == 0, r.stdout


def test_a_relative_link_is_read_against_the_document_s_own_stage(tmp_path):
    base = "https://docs.oasis-open.org/w/x/v1.0/csd01/"
    r = _pair(tmp_path, MD, '<p><a href="schemas/a.json">a</a></p>', f'<p><a href="{base}schemas/a.json">a</a></p>')
    assert r.returncode == 0, r.stdout
    r = _pair(tmp_path, MD, '<p><a href="schemas/b.json">a</a></p>', f'<p><a href="{base}schemas/a.json">a</a></p>')
    assert r.returncode == 1 and "csd01/schemas/b.json" in r.stdout
