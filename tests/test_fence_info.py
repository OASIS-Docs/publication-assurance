# Copyright 2026 OASIS Open
# SPDX-License-Identifier: Apache-2.0
# Authored by Michael Coletta, Technical Advisor to OASIS Open.
"""Step 1 and verify_md read a fence's info string as GitHub does.

A fence opened with a language name and more text (```yaml <!--json-path-->)
is a code block on GitHub and under pandoc's gfm and commonmark readers.
pandoc's markdown reader, which this repository's step 1 and verify_md use,
does not recognise it as a fence and collapses the block to inline code.
publisher-toolkit's step 1, the pipeline TC repositories pin, has rewritten
such openings before pandoc since v0.2.0 (lib/preprocess_md.py, May 2026);
this repository's copy of step 1 did not, so verify_md reported 96 of the
726 code blocks of CSAF v2.1 csd04 missing from a correct HTML (22 Oct 2026).
"""

from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys

import pytest

from conftest import FIXTURES, REPO_ROOT

FENCE_INFO = REPO_ROOT / ".github" / "src" / "pipeline" / "fence_info.py"
VERIFY = REPO_ROOT / "verify" / "verify_md.py"
STEP1 = REPO_ROOT / ".github" / "src" / "step_1_markdown_to_html_converter_V3_0.py"
EXCERPT = FIXTURES / "fence_info" / "csaf-v2.1-csd04-excerpt.md"

needs_pandoc = pytest.mark.skipif(
    shutil.which("pandoc") is None and not os.environ.get("REQUIRE_PANDOC"),
    reason="pandoc is not installed (CI sets REQUIRE_PANDOC=1)")


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_a_language_with_pandoc_attributes_is_left_alone():
    """pandoc's markdown reader reads ```yaml {.numberLines} as a fence and
    applies the attributes; cutting them would lose the line numbers."""
    fi = _load("fence_info_attrs", FENCE_INFO)
    md = '```yaml {.numberLines startFrom="5"}\na: 1\n```\n'
    assert fi.bare_fence_info(md) == (md, [])


def test_the_language_name_is_kept_and_the_trailing_text_dropped():
    fi = _load("fence_info", FENCE_INFO)
    md = "a\n\n```yaml <!--json-path($.a)-->\nx: 1\n```\n"
    out, lines = fi.bare_fence_info(md)
    assert out == "a\n\n```yaml\nx: 1\n```\n" and lines == [3]


def test_well_formed_fences_and_fence_bodies_are_left_alone():
    fi = _load("fence_info", FENCE_INFO)
    md = ("```yaml\nx: 1\n```\n\n~~~{.yaml title=\"t\"}\n```json not-a-fence-here\n~~~\n\n"
          "````md\n```yaml <!-- inside a longer fence -->\n````\n")
    assert fi.bare_fence_info(md) == (md, [])


def test_line_endings_and_indentation_survive():
    fi = _load("fence_info", FENCE_INFO)
    md = "  ~~~json  <!-- n -->\r\n{}\r\n  ~~~\r\n"
    assert fi.bare_fence_info(md) == ("  ~~~json\r\n{}\r\n  ~~~\r\n", [1])


def test_a_backtick_in_the_info_string_is_not_a_fence():
    """CommonMark: a backtick fence's info string may not contain a backtick."""
    fi = _load("fence_info", FENCE_INFO)
    md = "```yaml `x`\n"
    assert fi.bare_fence_info(md) == (md, [])


@needs_pandoc
def test_verify_md_reads_the_json_path_fence_as_a_code_block():
    vm = _load("verify_md", VERIFY)
    html = vm.md_to_html(str(EXCERPT))
    assert html.count("<pre") == 2, html
    assert "json-path" not in html


@needs_pandoc
def test_step1_publishes_the_json_path_fence_as_a_code_block(tmp_path):
    stage = tmp_path / "csaf" / "v2.1" / "csd04"
    stage.mkdir(parents=True)
    shutil.copy(EXCERPT, stage / "csaf-v2.1-csd04.md")
    r = subprocess.run([sys.executable, str(STEP1), str(stage / "csaf-v2.1-csd04.md"), str(tmp_path), str(stage),
                        "--md-to-html"], cwd=stage, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]
    html = (stage / "csaf-v2.1-csd04.html").read_text(encoding="utf-8")
    assert html.count("<pre") == 2 and "$schema: String" in html
    assert not [p.name for p in stage.iterdir() if p.name.startswith(".fence_info_")]
