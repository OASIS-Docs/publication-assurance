# Copyright 2026 OASIS Open
# SPDX-License-Identifier: Apache-2.0
# Authored by Michael Coletta, Technical Advisor to OASIS Open.
"""Every external tool the PDF step runs is bounded (base.run_tool).

toc_pages ran pdfinfo and pdftotext, and PipelineStep ran wkhtmltopdf and
pandoc, with no timeout: one tool that never exits held the step until the
job was killed, with nothing in the log to say which. publisher-toolkit, which
vendors this step, met the same failure in headless Chrome (the CSAF v2.1
CSD03 PDF was complete in about 10 s and the step was killed at 718.9 s).

Each case puts a fake tool first on PATH that starts a child and then waits
for it, and asserts the call returns within the bound, names the tool, and
leaves neither process running.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import time
import types

import pytest

from conftest import REPO_ROOT

PIPELINE = REPO_ROOT / ".github" / "src" / "pipeline"
BOUND = 1
HANG = 30  # seconds the fake tool would run if nothing stopped it


def load(name, package=False):
    """A pipeline module by path: standalone (as test_toc_pages and
    render/render.sh load toc_pages), or under a stand-in package (as the
    renderer and publisher-toolkit import it)."""
    if not package:
        spec = importlib.util.spec_from_file_location(f"_standalone_{name}", PIPELINE / f"{name}.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    if "pipeline" not in sys.modules:
        pkg = types.ModuleType("pipeline")
        pkg.__path__ = [str(PIPELINE)]
        sys.modules["pipeline"] = pkg
    spec = importlib.util.spec_from_file_location(f"pipeline.{name}", PIPELINE / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[f"pipeline.{name}"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def hanging(tmp_path, monkeypatch):
    """Put hanging pdfinfo, pdftotext and wkhtmltopdf first on PATH; return
    the file each writes its child's pid to."""
    bin_ = tmp_path / "bin"
    bin_.mkdir()
    pidfile = tmp_path / "child.pid"
    for tool in ("pdfinfo", "pdftotext", "wkhtmltopdf"):
        fake = bin_ / tool
        fake.write_text(f'#!/bin/sh\nsleep {HANG} &\necho $! > "{pidfile}"\nwait\n')
        fake.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_}{os.pathsep}{os.environ['PATH']}")
    return pidfile


def gone(pidfile):
    """True once the fake tool's child is no longer running."""
    pid = int(pidfile.read_text())
    for _ in range(40):
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return True
        time.sleep(0.05)
    return False


def bounded(call, tool):
    start = time.monotonic()
    with pytest.raises(subprocess.TimeoutExpired) as exc:
        call()
    elapsed = time.monotonic() - start
    assert elapsed < BOUND + 5, f"{tool} ran {elapsed:.1f} s against a {BOUND} s bound"
    assert f"{tool} did not finish within {BOUND} s" in str(exc.value), str(exc.value)


@pytest.mark.parametrize("call", ["dests", "text_pages"])
def test_a_hanging_poppler_tool_is_stopped_at_the_bound(tmp_path, hanging, monkeypatch, call):
    T = load("toc_pages")
    monkeypatch.setattr(T, "TOOL_TIMEOUT", BOUND)
    pdf = str(tmp_path / "spec.pdf")
    tool = {"dests": "pdfinfo", "text_pages": "pdftotext"}[call]
    bounded((lambda: T.dests(pdf)) if call == "dests" else (lambda: T.text_pages(pdf, [("s1", "one")])), tool)
    assert gone(hanging), f"{tool}'s child was left running"


def test_a_hanging_renderer_is_stopped_at_the_bound(tmp_path, hanging):
    base = load("base", package=True)

    class Step(base.PipelineStep):
        subprocess_timeout = BOUND

        def run(self):
            return self._run_subprocess(["wkhtmltopdf", "in.html", "out.pdf"], capture=True)

    bounded(Step().run, "wkhtmltopdf")
    assert gone(hanging), "wkhtmltopdf's child was left running"


def test_a_poppler_timeout_leaves_the_contents_unnumbered(tmp_path, monkeypatch):
    """PdfRenderer treats a timed-out pdfinfo as numbers it cannot read: the
    PDF keeps its unnumbered contents instead of the step failing."""
    pytest.importorskip("bs4", reason="the rendering pipeline requires bs4")
    base = load("base", package=True)
    toc = load("toc_pages", package=True)
    renderer = load("pdf_renderer", package=True)
    src = tmp_path / "spec.html"
    src.write_text('<html><head></head><body><h1 id="table-of-contents">Contents</h1>'
                   '<ul><li><a href="#s1">One</a></li></ul><h2 id="s1">One</h2></body></html>',
                   encoding="utf-8")

    def hang(*_):
        raise base.ToolTimeout(["pdfinfo", "-dests", "spec.pdf"], BOUND)

    monkeypatch.setattr(toc, "main", hang)
    printed = []
    step = renderer.PdfRenderer(str(src), str(tmp_path / "spec.pdf"))
    monkeypatch.setattr(step, "_convert_to_pdf", printed.append)
    step._number_contents()
    assert printed == [], "nothing to reprint when the numbers could not be read"


def test_toc_pages_still_runs_as_a_script():
    """Run by path (render/render.sh), toc_pages finds base.py beside it."""
    r = subprocess.run([sys.executable, str(PIPELINE / "toc_pages.py")], capture_output=True, text=True,
                       timeout=60)
    assert r.returncode == 1 and "Usage: toc_pages.py" in r.stderr, r.stderr
