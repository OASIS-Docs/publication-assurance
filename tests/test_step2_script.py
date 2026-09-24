"""The step 2 workflow script runs the pipeline TRANSFORMS.md documents.

.github/scripts/step_2_convert_html_to_pdf_V2_0.sh ran `wkhtmltopdf
--enable-local-file-access` on the HTML directly. It skipped the PDF
preprocessor (fix_html_for_pdf.py), so neither the inline-code wrap from
v1.4.2 nor the image cap from v1.5.0 reached its PDFs. It also skipped the A4
argument vector that PdfRenderer.build_command builds and tests/test_pdf_command.py pins.

This runs the real script on a copy of the CSAF v2.1 csd01 package, with a
stub wkhtmltopdf on PATH that records its argument vector and the file it was
asked to render.
"""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
import sys

import pytest

from conftest import CORPUS, REPO_ROOT

pytest.importorskip("bs4", reason="the preprocessor needs bs4, which CI installs")

SCRIPT = REPO_ROOT / ".github/scripts/step_2_convert_html_to_pdf_V2_0.sh"

STUB = """#!/usr/bin/env python3
import json, os, shutil, sys
args = sys.argv[1:]
log = os.environ["STUB_LOG"]
src = args[-2]
shutil.copy(src, log + ".input.html")
json.dump(args, open(log, "w"))
open(args[-1], "wb").write(b"%PDF-1.4 stub")
"""


@pytest.fixture
def run(tmp_path):
    pkg = tmp_path / "csaf/v2.1/csd01"
    shutil.copytree(CORPUS / "csaf/v2.1/csd01", pkg)
    (pkg / "csaf-v2.1-csd01.pdf").unlink()
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    stub = bin_dir / "wkhtmltopdf"
    stub.write_text(STUB)
    stub.chmod(stub.stat().st_mode | stat.S_IEXEC)
    log = tmp_path / "argv.json"
    env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}", "STUB_LOG": str(log),
           "PYTHON": sys.executable}

    def go():
        before = sorted(p.relative_to(pkg) for p in pkg.rglob("*"))
        r = subprocess.run(["bash", str(SCRIPT), str(pkg)], env=env, capture_output=True,
                           text=True, cwd=tmp_path)
        after = sorted(p.relative_to(pkg) for p in pkg.rglob("*"))
        import json
        argv = json.loads(log.read_text()) if log.exists() else []
        rendered = (tmp_path / "argv.json.input.html").read_text() if argv else ""
        return r, argv, rendered, before, after
    return go, pkg


def test_the_script_renders_with_the_documented_a4_argument_vector(run):
    go, pkg = run
    r, argv, _, _, _ = go()
    assert r.returncode == 0, r.stdout + r.stderr
    assert argv[argv.index("--page-size") + 1] == "A4", argv
    assert argv[argv.index("--margin-left") + 1] == "20mm", argv
    assert argv[-1] == str(pkg / "csaf-v2.1-csd01.pdf"), argv


def test_the_script_renders_the_preprocessed_html(run):
    go, _ = run
    r, _, rendered, _, _ = go()
    assert r.returncode == 0, r.stdout + r.stderr
    assert "TARGETED MONOSPACE FIXES" in rendered
    assert "max-width: 100% !important" in rendered


def test_the_footer_names_the_published_file_not_the_intermediate(run):
    go, _ = run
    _, argv, _, _, _ = go()
    assert argv[argv.index("--footer-left") + 1] == "csaf-v2.1-csd01.html", argv


def test_the_script_leaves_only_the_pdf_behind(run):
    go, pkg = run
    r, _, _, before, after = go()
    assert r.returncode == 0, r.stdout + r.stderr
    assert set(after) - set(before) == {pkg.joinpath("csaf-v2.1-csd01.pdf").relative_to(pkg)}
    r2, argv2, _, _, _ = go()                 # a second run picks the same source
    assert argv2[-1].endswith("csaf-v2.1-csd01.pdf") and r2.returncode == 0
