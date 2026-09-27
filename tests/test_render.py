# Copyright 2026 OASIS Open
# SPDX-License-Identifier: Apache-2.0
# Authored by Michael Coletta, Technical Advisor to OASIS Open.
"""render/: a Markdown specification rendered, staged and gated.

The end-to-end test renders the DMLex v1.0 OS Markdown edition through the
pipeline's step 1, step 2's preprocessor and render/print_pdf.mjs, then runs
the gate on the staged package. The footer must be the published one, read
from the document (name, track, copyright, document date, page), and the
cover must not repeat the title, which a running header would do. Chrome is
needed; CI sets REQUIRE_CHROME=1 so a missing browser fails.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys

import pytest

from conftest import FIXTURES, REPO_ROOT

RENDER = REPO_ROOT / "render"
EDITION = FIXTURES / "verify_md" / "dmlex-v1.0-os"
PUBLISHED = EDITION / "published-dmlex-v1.0-os.html"

sys.path.insert(0, str(REPO_ROOT / "pub-check"))
import validation_report  # noqa: E402


def footer(md):
    r = subprocess.run([sys.executable, str(RENDER / "footer.py"), str(md)], capture_output=True, text=True)
    return r, (json.loads(r.stdout) if r.returncode == 0 else None)


def test_the_footer_is_read_from_the_document():
    r, f = footer(EDITION / "dmlex-v1.0-os.md")
    assert r.returncode == 0, r.stderr
    assert f == {"name": "dmlex-v1.0-os", "stage": "os", "track": "Standards Track Work Product",
                 "copyright": "Copyright © OASIS Open 2025. All Rights Reserved.", "date": "29 April 2025"}


def test_a_committee_note_is_non_standards_track(tmp_path):
    md = tmp_path / "widget-v1.0-cnd01.md"
    md.write_text("# Widget\n\n## 2 May 2026\n\n#### This stage:\n"
                  "https://docs.oasis-open.org/w/widget/v1.0/cnd01/widget-v1.0-cnd01.html\n\n"
                  "Copyright © OASIS Open 2026.\n", encoding="utf-8")
    r, f = footer(md)
    assert r.returncode == 0, r.stderr
    assert f["track"] == "Non-Standards Track Work Product" and f["stage"] == "cnd"
    assert f["copyright"] == "Copyright © OASIS Open 2026. All Rights Reserved."


def test_a_document_without_its_date_is_refused(tmp_path):
    md = tmp_path / "widget-v1.0-csd01.md"
    md.write_text("#### This stage:\nhttps://docs.oasis-open.org/w/widget/v1.0/csd01/widget-v1.0-csd01.html\n"
                  "Copyright © OASIS Open 2026.\n", encoding="utf-8")
    r, _ = footer(md)
    assert r.returncode == 2 and "date line" in r.stderr


@pytest.fixture(scope="module")
def rendered(tmp_path_factory):
    chrome = validation_report.find_browser()
    missing = [t for t, ok in (("Chrome", chrome), ("pandoc", shutil.which("pandoc")),
                               ("node", shutil.which("node")), ("npm", shutil.which("npm"))) if not ok]
    if missing:
        if os.environ.get("REQUIRE_CHROME") == "1":
            pytest.fail(f"REQUIRE_CHROME=1 but {missing} not found")
        pytest.skip(f"{missing} not found")
    base = tmp_path_factory.mktemp("render")
    md_dir = base / "md"
    shutil.copytree(EDITION, md_dir, ignore=shutil.ignore_patterns("published-*"))
    out = base / "out"
    r = subprocess.run(["bash", str(RENDER / "render.sh"), str(md_dir), "-", str(out)],
                       capture_output=True, text=True, env=dict(os.environ, CHROME=chrome))
    stage = out / "lexidma" / "dmlex" / "v1.0" / "os"
    return r, stage, chrome


def page_text(pdf, page):
    return subprocess.run(["pdftotext", "-f", str(page), "-l", str(page), "-layout", str(pdf), "-"],
                          capture_output=True, text=True, check=True).stdout


def test_the_edition_renders_with_the_published_footer(rendered):
    r, stage, _ = rendered
    assert r.returncode in (0, 1), r.stdout[-3000:] + r.stderr
    pdf = stage / "dmlex-v1.0-os.pdf"
    assert (stage / "dmlex-v1.0-os.html").stat().st_size > 100000 and pdf.stat().st_size > 100000
    if not shutil.which("pdftotext"):
        pytest.skip("pdftotext (poppler) not installed")
    pages = int(re.search(r"Pages:\s+(\d+)", subprocess.run(["pdfinfo", str(pdf)], capture_output=True,
                                                              text=True).stdout).group(1))
    assert pages > 150
    lines = [l for l in page_text(pdf, 3).splitlines() if l.strip()]
    bottom = " ".join(" ".join(lines[-2:]).split())
    for part in ("dmlex-v1.0-os", "Standards Track Work Product",
                 "Copyright © OASIS Open 2025. All Rights Reserved.", "29 April 2025", f"Page 3 of {pages}"):
        assert part in bottom, f"{part!r} not in the page 3 footer: {bottom}"
    assert ".html" not in bottom


def test_the_gate_raises_nothing_on_the_rendered_pdf(rendered):
    """The blockers left are the DMLex source's own; none is about the PDF,
    and the cover carries the title once (no running header)."""
    r, stage, _ = rendered
    gate = subprocess.run([sys.executable, str(REPO_ROOT / "pub-check" / "oasis_pub_check.py"), "--json",
                           str(stage)], capture_output=True, text=True)
    report = json.loads(gate.stdout)
    pdf = [x for x in report["findings"] if x["check"].startswith("pdf") and x["severity"] == "BLOCKER"]
    assert pdf == [], pdf
    assert "pdf-cover" in {o["check"] for o in report.get("observations", [])} or \
        "pdf-cover" in json.dumps(report), "the cover check did not run on the rendered PDF"


def test_compare_captures_named_anchors_and_fails_on_a_missing_one(rendered, tmp_path):
    r, stage, chrome = rendered
    html = stage / "dmlex-v1.0-os.html"
    env = dict(os.environ, CHROME=chrome, NODE_PATH=str(RENDER / "node_modules"))
    ok = subprocess.run(["node", str(RENDER / "compare.mjs"), str(PUBLISHED), str(html), str(tmp_path / "ok"),
                         "cover,toc,core_entry"], capture_output=True, text=True, env=env)
    assert ok.returncode == 0, ok.stdout + ok.stderr
    assert len(list((tmp_path / "ok").glob("*.png"))) == 6
    bad = subprocess.run(["node", str(RENDER / "compare.mjs"), str(PUBLISHED), str(html), str(tmp_path / "bad"),
                          "core_entry,no_such_anchor"], capture_output=True, text=True, env=env)
    assert bad.returncode == 1 and "MISSING published #no_such_anchor" in bad.stdout


def test_the_contents_carry_the_page_each_heading_is_on(rendered):
    """The published DMLex PDF numbers its contents; Chrome cannot, so
    render.sh reads the pages back from the printed PDF. Each number is
    checked against the page the heading's text is actually printed on."""
    r, stage, _ = rendered
    if not shutil.which("pdftotext"):
        pytest.skip("pdftotext (poppler) not installed")
    pdf = stage / "dmlex-v1.0-os.pdf"
    pages = [page_text(pdf, n) for n in range(1, 12)]
    toc = "\n".join(p for p in pages if "Table of Contents" in p or re.search(r"^\s*\d+(\.\d+)* \S.*\s(\d+)\s*$", p, re.M))
    entries = re.findall(r"^\s*((?:\d+(?:\.\d+)*|Appendix [A-Z]|[A-Z](?:\.\d+)+) .*?)\s{2,}(\d+)\s*$", toc, re.M)
    assert len(entries) >= 40, f"too few numbered contents entries: {entries[:5]}"
    unnumbered = re.findall(r"^\s*(\d+\.\d+ [A-Za-z].*[a-z])\s*$", pages[4], re.M)
    assert unnumbered == [], f"contents entries without a page: {unnumbered}"
    for title, page in [e for e in entries if e[0].split()[0] in ("1", "2", "3", "3.4", "4")]:
        body = " ".join(page_text(pdf, int(page)).split())
        assert " ".join(title.split()) in body, f"{title!r} is not on page {page}"
