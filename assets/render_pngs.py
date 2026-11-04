#!/usr/bin/env python3
# Copyright 2026 OASIS Open
# SPDX-License-Identifier: Apache-2.0
# Authored by Michael Coletta, Technical Advisor to OASIS Open.
"""Render the committed diagram SVGs to the 2x PNGs the documents show.

The SVG beside each PNG is its source. The PNGs are not rebuilt in CI
(rsvg-convert output is not byte-stable across versions), so they drifted:
the SVGs were brought to 186 checks at v1.16.0 while the PNGs still showed
181 (issue #92). Run this whenever an SVG changes, then look at the PNGs.

Before rendering, the check and class counts each SVG advertises are compared
with `oasis_pub_check.py --list-checks`; a stale SVG stops the run, so a
fresh PNG cannot carry an old number.

    python3 assets/render_pngs.py            # render every SVG
    python3 assets/render_pngs.py hero.svg   # render named SVGs only

Needs rsvg-convert (librsvg) and the Poppins and IBM Plex Mono fonts.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

ASSETS = Path(__file__).resolve().parent
REPO = ASSETS.parent
CHECKER = REPO / "pub-check" / "oasis_pub_check.py"

COUNT_LINE = re.compile(r"(\d+) individual checks across (\d+) check classes")
CHECK_CLAIM = re.compile(r"(\d+) checks")
CLASS_CLAIM = re.compile(r"(\d+) (?:check )?classes")


def live_counts() -> tuple[int, int]:
    out = subprocess.run([sys.executable, str(CHECKER), "--list-checks"],
                         capture_output=True, text=True, check=True).stdout
    m = COUNT_LINE.search(out)
    if not m:
        sys.exit("render_pngs: --list-checks printed no count line")
    return int(m.group(1)), int(m.group(2))


def stale_claims(svg: Path, checks: int, classes: int) -> list[str]:
    text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", svg.read_text("utf-8")))
    bad = [f"{m.group(0)!r} (live: {checks})"
           for m in CHECK_CLAIM.finditer(text) if int(m.group(1)) != checks]
    bad += [f"{m.group(0)!r} (live: {classes})"
            for m in CLASS_CLAIM.finditer(text) if int(m.group(1)) != classes]
    return bad


def shown(p: Path) -> str:
    return str(p.relative_to(REPO)) if p.is_relative_to(REPO) else str(p)


def main(argv: list[str]) -> int:
    if not shutil.which("rsvg-convert"):
        print("render_pngs: rsvg-convert is not installed", file=sys.stderr)
        return 2
    svgs = ([ASSETS / a if not Path(a).is_absolute() else Path(a) for a in argv]
            or sorted(ASSETS.rglob("*.svg")))
    checks, classes = live_counts()
    problems = {s: stale_claims(s, checks, classes) for s in svgs}
    problems = {s: p for s, p in problems.items() if p}
    if problems:
        for s, p in problems.items():
            print(f"{shown(s)}: stale count {', '.join(p)}", file=sys.stderr)
        print("render_pngs: update the SVGs first; nothing was rendered", file=sys.stderr)
        return 1
    for svg in svgs:
        png = svg.with_suffix(".png")
        subprocess.run(["rsvg-convert", "-z", "2", str(svg), "-o", str(png)], check=True)
        print(f"rendered {shown(png)}")
    print(f"counts: {checks} checks across {classes} classes")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
