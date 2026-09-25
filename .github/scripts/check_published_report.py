#!/usr/bin/env python3
# Copyright 2026 OASIS Open
# SPDX-License-Identifier: Apache-2.0
# Authored by Michael Coletta, Technical Advisor to OASIS Open.
"""Prove the report links the action published open for a reader.

CI runs the action with publishing on, then this script requests every URL
the action stated, the way a reader's browser does (no token), and fetches
the PDF's raw bytes to check it is the whole report: a PDF whose text layer
names every check class --list-checks prints.

    check_published_report.py --pdf URL --md URL --folder URL --pinned URL
                              [--html URL] [--html-wait SECONDS]

Exit 0 when every URL answers 200 and the PDF is complete, 1 otherwise.
Standard library plus pdftotext (poppler).
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

ROOT = __file__.rsplit("/.github/", 1)[0]


def status(url: str) -> int:
    req = urllib.request.Request(url, method="GET", headers={"User-Agent": "pub-check-ci"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status
    except urllib.error.HTTPError as exc:
        return exc.code
    except (urllib.error.URLError, OSError):
        return 0


def wait_for_200(url: str, seconds: float) -> int:
    deadline = time.monotonic() + seconds
    while True:
        code = status(url)
        if code == 200 or time.monotonic() > deadline:
            return code
        time.sleep(5)


def raw_url(pinned: str) -> str:
    """https://github.com/<o>/<r>/blob/<sha>/<path> -> raw.githubusercontent.com"""
    m = re.fullmatch(r"https://github\.com/([^/]+/[^/]+)/blob/([0-9a-f]{40})/(.+)", pinned)
    if not m:
        raise SystemExit(f"FAIL: not a pinned blob URL: {pinned}")
    return f"https://raw.githubusercontent.com/{m.group(1)}/{m.group(2)}/{m.group(3)}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    for name in ("pdf", "md", "folder", "pinned"):
        ap.add_argument(f"--{name}", required=True)
    ap.add_argument("--html", default="")
    ap.add_argument("--html-wait", type=float, default=0)
    a = ap.parse_args()
    failed = False
    urls = [a.pdf, a.md, a.folder, a.pinned]
    for url in urls:
        code = wait_for_200(url, 30)
        print(f"{code} {url}")
        failed |= code != 200
    if a.html:
        # A Pages site rebuilds after each push; give it time to serve.
        code = wait_for_200(a.html, a.html_wait)
        print(f"{code} {a.html}")
        failed |= code != 200

    raw = raw_url(a.pinned)
    with tempfile.NamedTemporaryFile(suffix=".pdf") as f:
        with urllib.request.urlopen(raw, timeout=60) as r:
            f.write(r.read())
        f.flush()
        head = open(f.name, "rb").read(5)
        text = re.sub(r"\s+", "", subprocess.run(["pdftotext", f.name, "-"], capture_output=True,
                                                 text=True).stdout)
    listing = subprocess.run([sys.executable, f"{ROOT}/pub-check/oasis_pub_check.py",
                              "--list-checks"], capture_output=True, text=True).stdout
    classes = re.findall(r"(?m)^  ([a-z0-9-]+)\s+\d+$", listing)
    missing = [c for c in classes if c not in text]
    print(f"raw PDF {raw}: starts {head!r}; {len(classes)} check classes, missing {missing}")
    failed |= head != b"%PDF-" or not classes or bool(missing)
    print("FAIL" if failed else "PASS")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
