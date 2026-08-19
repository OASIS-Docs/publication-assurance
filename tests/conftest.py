"""Pytest config for the oasis-pub-check acceptance criteria.

`pub-check/` is a hyphenated directory, so the checker cannot be imported as a
package. It is loaded here by path and exposed as `oasis_pub_check`, alongside
the on-disk fixture root and a subprocess helper for the CLI contract tests.

The CSAF regression corpus under examples/ is the sanctioned fixture material.
It is copied into a tmp_path per test rather than duplicated under fixtures/,
because the corpus carries multi-megabyte PDFs and the tests that use it write
into the directory they check.
"""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures"
PUB_CHECK = REPO_ROOT / "pub-check" / "oasis_pub_check.py"
CORPUS = REPO_ROOT / "examples"


def _load_checker():
    spec = importlib.util.spec_from_file_location("oasis_pub_check", PUB_CHECK)
    module = importlib.util.module_from_spec(spec)
    sys.modules["oasis_pub_check"] = module
    spec.loader.exec_module(module)
    return module


oasis_pub_check = _load_checker()


def run_cli(*args: str) -> subprocess.CompletedProcess:
    """Invoke the checker exactly as CI and the runbook do: as a script."""
    return subprocess.run(
        [sys.executable, str(PUB_CHECK), *args],
        capture_output=True, text=True,
    )


DIRECTORY_LISTING = """<!DOCTYPE html>
<html><head><title>Index of {path}</title></head>
<body><h1>Index of {path}</h1>
<ul>{entries}</ul>
</body></html>
"""


def stage_from_corpus(dest: Path, corpus_stage: Path, *,
                      rename_stem: str | None = None,
                      with_index: bool = False) -> Path:
    """Copy one corpus stage directory into `dest` and return the stage dir.

    `rename_stem` re-stems the delivery items, which is how a real package
    reaches the shortest-stem fallback in find_delivery_items: an `os/`
    directory holding `UBL-2.5.html` has no file whose stem ends in `-os`.
    `with_index` adds the generated directory listing that every DEPLOYED
    OASIS tree carries, which is the confounder the fallback used to select.
    """
    dest.mkdir(parents=True, exist_ok=True)
    stage = dest / corpus_stage.parent.name / corpus_stage.name
    shutil.copytree(corpus_stage, stage)
    if rename_stem:
        for item in sorted(stage.iterdir()):
            if item.is_file():
                item.rename(stage / f"{rename_stem}{item.suffix}")
    if with_index:
        entries = "".join(
            f'<li><a href="{p.name}">{p.name}</a></li>'
            for p in sorted(stage.iterdir()) if p.is_file()
        )
        listing = stage / "index.html"
        listing.write_text(
            DIRECTORY_LISTING.format(path=f"/{stage.parent.name}/{stage.name}",
                                     entries=entries),
            encoding="utf-8")
    return stage
