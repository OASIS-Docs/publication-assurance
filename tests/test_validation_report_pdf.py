"""The Validation Report's PDF carries the whole report in its text layer.

validation_report.py --pdf prints the HTML report with headless Chrome. A PDF
that looks right can still have lost rows to a page break, a clipped cell or
a print stylesheet, so these tests read the PDF's own text layer and compare
it with the inventory --list-checks prints.

The render test skips only where no Chrome or Chromium exists. CI sets
REQUIRE_CHROME=1 in the jobs that run it, and there a skip is a failure.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys

import pytest

from conftest import CORPUS, REPO_ROOT, run_cli, stage_from_corpus
from test_validation_report import list_checks

REPORT = REPO_ROOT / "pub-check" / "validation_report.py"
CSAF_CSD01 = CORPUS / "csaf" / "v2.1" / "csd01"

sys.path.insert(0, str(REPO_ROOT / "pub-check"))
import validation_report  # noqa: E402


def pdf_text(path) -> str:
    """The PDF's text layer, from pdftotext (poppler) or PyMuPDF."""
    if shutil.which("pdftotext"):
        out = subprocess.run(["pdftotext", str(path), "-"], capture_output=True, text=True)
        assert out.returncode == 0, out.stderr
        return out.stdout
    fitz = pytest.importorskip("fitz", reason="neither pdftotext nor PyMuPDF is installed")
    return "".join(page.get_text() for page in fitz.open(str(path)))


def squash(text: str) -> str:
    """Text without whitespace: a cell wrapped across lines still matches."""
    return re.sub(r"\s+", "", text)


def require_browser() -> None:
    if not validation_report.find_browser():
        if os.environ.get("REQUIRE_CHROME") == "1":
            pytest.fail("REQUIRE_CHROME=1 but no Chrome or Chromium was found")
        pytest.skip("no Chrome or Chromium on this machine")


def test_the_pdf_carries_every_check_class_and_condition(tmp_path):
    require_browser()
    stage = stage_from_corpus(tmp_path / "pkg", CSAF_CSD01)
    gate = run_cli("--json", str(stage))
    assert gate.returncode in (0, 1), gate.stderr
    (tmp_path / "r.json").write_text(gate.stdout)
    pdf = tmp_path / "pubcheck-validation.pdf"
    result = subprocess.run(
        [sys.executable, str(REPORT), str(tmp_path / "r.json"), "--md", str(tmp_path / "o.md"),
         "--pdf", str(pdf), "--title", "CSAF v2.1 CSD01"], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert pdf.read_bytes().startswith(b"%PDF-"), result.stderr

    text = squash(pdf_text(pdf))
    inventory = list_checks()
    assert len(inventory) > 50
    missing = sorted(c for c in inventory if c not in text)
    assert not missing, f"check classes absent from the PDF text layer: {missing}"

    # pdftotext joins a word the browser wrapped after a hyphen without the
    # hyphen ("two-" / "digit" reads "twodigit"), so the cell comparison
    # drops hyphens on both sides. Class names never wrap and keep theirs.
    record = validation_report.build_record(json.loads(gate.stdout), "t", None, "d")
    assert len(record["condition_detail"]) == sum(inventory.values())
    flat = text.replace("-", "")
    lost = [(r["check"], field) for r in record["condition_detail"]
            for field in ("condition", "observed", "compares_to")
            if squash(r[field]).replace("-", "") not in flat]
    assert not lost, f"condition cells absent from the PDF text layer: {lost}"
    assert re.search(r"Page\s*1\s*of\s*\d+", pdf_text(pdf)), "footer page numbering missing"


def test_no_browser_means_no_pdf_a_warning_and_the_same_exit(tmp_path):
    """A runner without Chrome still gets its Markdown report and exit 0."""
    stage = stage_from_corpus(tmp_path / "pkg", CSAF_CSD01)
    gate = run_cli("--json", str(stage))
    (tmp_path / "r.json").write_text(gate.stdout)
    pdf, md = tmp_path / "o.pdf", tmp_path / "o.md"
    env = {**os.environ, "PUBCHECK_CHROME": str(tmp_path / "no-such-browser")}
    result = subprocess.run([sys.executable, str(REPORT), str(tmp_path / "r.json"),
                             "--md", str(md), "--pdf", str(pdf)],
                            capture_output=True, text=True, env=env)
    assert result.returncode == 0, result.stderr
    assert md.stat().st_size > 0
    assert not pdf.exists()
    assert "PDF not written" in result.stderr


def test_a_row_taller_than_a_page_loses_no_line(tmp_path):
    """Red-team counterexample: a 200-line observed value and a 10,000
    character token with no break opportunity, each in a row taller than a
    page. Every line and every character must reach the text layer."""
    require_browser()
    lines = "\n".join(f"line {i} of a very long observed value" for i in range(200))
    token = "X" * 10000
    data = {"target": "t", "observed": {},
            "findings": [{"severity": "WARN", "check": "x", "message": f"tall:\n{lines}"},
                         {"severity": "BLOCKER", "check": "y", "message": f"wide: {token}"}],
            "conditions": [{"check": "x", "sig": "tall", "applies": "all", "condition": "c",
                            "pulls": "p", "compares_to": "e"},
                           {"check": "y", "sig": "wide", "applies": "all", "condition": "d",
                            "pulls": "p", "compares_to": "e"}]}
    (tmp_path / "r.json").write_text(json.dumps(data))
    pdf = tmp_path / "o.pdf"
    result = subprocess.run([sys.executable, str(REPORT), str(tmp_path / "r.json"),
                             "--md", str(tmp_path / "o.md"), "--pdf", str(pdf)],
                            capture_output=True, text=True)
    assert result.returncode == 0 and pdf.exists(), result.stderr
    text = pdf_text(pdf)
    # A line wrapped across a page break has the footer between its halves,
    # so count the "line N of" heads: once in the class table, once below.
    heads = re.findall(r"line\s+(\d+)\s+of", text)
    short = [n for n in range(200) if heads.count(str(n)) < 2]
    assert not short, f"lines missing from the PDF: {short}"
    assert text.count("X") == 2 * len(token)


def test_a_hung_browser_times_out_and_leaves_no_process_behind(tmp_path):
    """Red-team counterexample: a browser that never answers. The report must
    still exit 0 without a PDF, and no process the browser started may
    outlive it."""
    if validation_report.fcntl is None:
        pytest.skip("the PDF step is POSIX-only")
    pidfile = tmp_path / "child.pid"
    fake = tmp_path / "hung-browser"
    fake.write_text(f"#!/bin/sh\nsleep 300 &\necho $! > {pidfile}\nwait\n")
    fake.chmod(0o755)
    (tmp_path / "r.json").write_text(json.dumps({
        "target": "t", "observed": {}, "findings": [],
        "conditions": [{"check": "x", "sig": "s", "applies": "all", "condition": "c",
                        "pulls": "p", "compares_to": "e"}]}))
    pdf = tmp_path / "o.pdf"
    env = {**os.environ, "PUBCHECK_CHROME": str(fake), "PUBCHECK_PDF_TIMEOUT": "2"}
    result = subprocess.run([sys.executable, str(REPORT), str(tmp_path / "r.json"),
                             "--md", str(tmp_path / "o.md"), "--pdf", str(pdf)],
                            capture_output=True, text=True, env=env, timeout=60)
    assert result.returncode == 0, result.stderr
    assert not pdf.exists()
    assert "within 2s" in result.stderr, result.stderr
    child = int(pidfile.read_text())
    with pytest.raises(ProcessLookupError):
        os.kill(child, 0)
