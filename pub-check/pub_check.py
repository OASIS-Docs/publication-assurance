#!/usr/bin/env python3
# Copyright 2025-2026 OASIS Open
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Authored by Michael Coletta, Technical Advisor to OASIS Open.
"""pub_check: OASIS publication-readiness checker for TC work-product packages.

Validation is on the output. All roads lead to HTML and PDF: whatever the
authoring format (Markdown, Word, DocBook/XML, LaTeX, ...), the published form
is HTML + PDF at the canonical URLs, and the bulk of the gate runs on those
outputs for every package. Source-format checks are add-ons applied to
whatever source the package carries: markdown add-ons for .md, Word
render-fidelity add-ons for .docx. Source-only checks never false-fire on a
package that lacks that source.

Runs the checks TC Administration applies to a submitted work-product package
BEFORE publication to docs.oasis-open.org, so a TC can run them in its own
build (make target, CI job, pre-vote gate) and submit packages that publish
without a review round-trip.

Every check corresponds to a finding that has actually bounced or delayed a
real submission. Stdlib only. No configuration file: everything is derived
from the package itself.

Usage:
    pub_check.py <stage-dir | package.zip> [--json] [--emit-manifest]

The stage directory is the directory that will be published, e.g.
    openeox/eox-core/v1.0/csd01/
containing the delivery items (.md, .html, .pdf) and any schema/ subtree.

Exit status: 0 = publishable (warnings allowed), 1 = blockers found.

Author: Michael Coletta, Technical Advisor to OASIS Open.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from html.parser import HTMLParser

__author__ = "Michael Coletta <michael.coletta@oasis-open.org>"

SITE = "https://docs.oasis-open.org"

# Naming Directives (current, since v1.7 of 2 Jan 2024): a document in public
# review KEEPS its stage name. csprd/cnprd/cos are retired; csdpr never existed.
VALID_STAGE_PREFIXES = {"wd", "csd", "cs", "cnd", "cn", "os", "ps", "psd", "pn", "pnd", "errata"}
RETIRED_STAGE_TOKENS = {"csprd", "cnprd", "cos", "csdpr", "cndpr"}

BLOCKER, WARN, INFO = "BLOCKER", "WARN", "INFO"


class Findings:
    def __init__(self) -> None:
        self.items: list[dict] = []

    def add(self, severity: str, check: str, message: str) -> None:
        self.items.append({"severity": severity, "check": check, "message": message})

    @property
    def blockers(self) -> int:
        return sum(1 for f in self.items if f["severity"] == BLOCKER)


class _AnchorParser(HTMLParser):
    """Collect element ids, <a name=...>, internal hrefs, and the <title>."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ids: set[str] = set()
        self.internal_hrefs: list[str] = []
        self.title = ""
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if "id" in d:
            self.ids.add(d["id"])
        if tag == "a" and "name" in d:
            self.ids.add(d["name"])
        if tag == "a" and d.get("href", "").startswith("#"):
            self.internal_hrefs.append(d["href"][1:])
        if tag == "title":
            self._in_title = True

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def read_text(path: str) -> str:
    with open(path, encoding="utf-8", errors="replace") as fh:
        return fh.read()


def strip_code_blocks(text: str, kind: str) -> str:
    """Blank out fenced/code content so residue and link checks only see prose.
    Replacement preserves line numbers."""

    def blank(m: re.Match) -> str:
        return "\n" * m.group(0).count("\n")

    if kind == "md":
        text = re.sub(r"^(```|~~~).*?^\1\s*$", blank, text, flags=re.M | re.S)
        text = re.sub(r"(?<!`)`[^`\n]+`(?!`)", " ", text)
    else:
        text = re.sub(r"<pre\b.*?</pre>", blank, text, flags=re.S | re.I)
        text = re.sub(r"<code\b.*?</code>", blank, text, flags=re.S | re.I)
    return text


def find_delivery_items(stage_dir: str,
                        exts: tuple[str, ...] = ("md", "html", "pdf")) -> dict[str, str]:
    """Map extension -> path for the DELIVERY items in dir root.

    A stage directory legitimately carries auxiliary artifacts next to the
    delivery items (comment-resolution logs, -DIFF PDFs, public-review
    metadata, namespace pages). The delivery item per format is the file
    whose stem ends in -<stage>; if none does, fall back to the shortest
    stem (covers pre-rename working packages so the filename check can
    report them). The default extension set is the markdown track; the
    DOCX-native track asks for (docx, html, pdf)."""
    stage = os.path.basename(os.path.normpath(stage_dir))
    cands: dict[str, list[str]] = {e: [] for e in exts}
    for name in sorted(os.listdir(stage_dir)):
        p = os.path.join(stage_dir, name)
        if not os.path.isfile(p):
            continue
        ext = os.path.splitext(name)[1].lstrip(".").lower()
        if ext in cands:
            cands[ext].append(p)
    out: dict[str, str] = {}
    for ext, paths in cands.items():
        if not paths:
            continue
        exact = [p for p in paths
                 if os.path.splitext(os.path.basename(p))[0].endswith(f"-{stage}")]
        pool = exact or paths
        out[ext] = min(pool, key=lambda p: len(os.path.basename(p)))
    return out


def auxiliary_files(stage_dir: str, items: dict[str, str]) -> list[str]:
    delivery = {os.path.basename(p) for p in items.values()}
    out = []
    for name in sorted(os.listdir(stage_dir)):
        if os.path.isfile(os.path.join(stage_dir, name)) and name not in delivery:
            out.append(name)
    return out


def parse_stage(stage_dir: str) -> tuple[str, str]:
    """Return (version, stage). The version is the nearest ancestor directory
    matching vN.N, so errata paths (.../v2.0/errata01/os) parse correctly."""
    norm = os.path.normpath(stage_dir)
    stage = os.path.basename(norm)
    version = os.path.basename(os.path.dirname(norm))
    probe = os.path.dirname(norm)
    while probe and os.path.basename(probe):
        if re.fullmatch(r"v\d+(\.\d+)+", os.path.basename(probe)):
            version = os.path.basename(probe)
            break
        probe = os.path.dirname(probe)
    return version, stage


def stage_urls_from_md(md_text: str, heading: str) -> list[str]:
    """URLs under a front-matter heading. 'This' matches This Stage/This Version
    (the template wording changed); same for 'Latest'."""
    m = re.search(rf"^#+ {heading} (?:Stage|Version)\b.*?$(.*?)^#+ ",
                  md_text, re.M | re.S | re.I)
    if not m:
        return []
    return re.findall(r"https?://\S+?(?=[)\s\\]|$)", m.group(1))


# ---------------------------------------------------------------- checks

def check_stage_name(stage: str, f: Findings) -> None:
    m = re.fullmatch(r"([a-z]+)(\d\d)?", stage)
    prefix = m.group(1) if m else stage
    if m and prefix in VALID_STAGE_PREFIXES and prefix != "os" and not m.group(2):
        f.add(BLOCKER, "stage-name",
              f"Stage '{stage}' is missing its two-digit number (e.g. {prefix}01).")
    if prefix in RETIRED_STAGE_TOKENS:
        f.add(BLOCKER, "stage-name",
              f"Stage '{stage}' uses a retired/invalid stage token. Current naming: a document "
              f"in public review keeps its stage name (csd stays csd). Valid: "
              f"{', '.join(sorted(VALID_STAGE_PREFIXES))} + two digits.")
    elif prefix not in VALID_STAGE_PREFIXES:
        f.add(BLOCKER, "stage-name", f"Stage '{stage}' is not a recognized stage token.")


def check_version_naming(version: str, stem: str, f: Findings) -> None:
    """Naming Directives: the version directory is vN.N(.N) and the delivery
    stem carries it (<base>-v<X.Y>-<stage>). A stem whose embedded version
    disagrees with the directory is a stale-rename tell."""
    if not re.fullmatch(r"v\d+(\.\d+)+", version):
        f.add(BLOCKER, "version-naming",
              f"Version directory '{version}' does not match the vN.N convention "
              f"(e.g. v1.0, v2.0.1). The version segment binds the URI, the "
              f"filenames, and the citations.")
        return
    if stem and f"-{version}-" not in f"{stem}-":
        m = re.search(r"-v(\d+(\.\d+)+)-", stem)
        if m and f"v{m.group(1)}" != version:
            f.add(BLOCKER, "version-naming",
                  f"Delivery filename '{stem}' embeds version v{m.group(1)} but the "
                  f"package publishes under /{version}/ — the files were renamed "
                  f"from a different version's package.")
        else:
            f.add(WARN, "version-naming",
                  f"Delivery filename '{stem}' does not embed the version segment "
                  f"'-{version}-' (Naming Directives shape: <base>-{version}-<stage>).")


def check_revision_collision(base: str, version: str, stage: str,
                             f: Findings) -> None:
    """A new submission's stage must not already exist on the live site: the
    revision increments instead (a 'CSD01' that has been live since 2024 is
    the next package's csd02 — the KMIP v3.0 scar, Jul 2026). Network-derived
    and advisory: WARN on collision, INFO listing the version's published
    stages, silent skip offline (set PUB_CHECK_OFFLINE=1 to force-skip)."""
    if os.getenv("PUB_CHECK_OFFLINE", "").lower() in {"1", "true", "yes"}:
        return
    if not base or not base.startswith(SITE + "/"):
        return
    import urllib.error
    import urllib.request

    def fetch(url: str) -> tuple[int, str]:
        req = urllib.request.Request(url, headers={"User-Agent": "pub-check"})
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                return r.status, r.read(65536).decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            return e.code, ""
        except Exception:
            return 0, ""

    status, _ = fetch(base)
    if status == 200:
        f.add(WARN, "revision-collision",
              f"Stage /{stage}/ is already published at {base} — a NEW submission "
              f"for {version} must use the next revision number instead. Ignore "
              f"this warning if you are re-checking the published package itself.")
    version_url = base.split(f"/{stage}/", 1)[0] + "/"
    status, listing = fetch(version_url)
    if status == 200 and listing:
        stages = sorted(set(re.findall(
            r'href="((?:wd|csd|cs|cnd|cn|os|ps|psd|pn|pnd|errata)\d*)/"', listing)))
        if stages:
            f.add(INFO, "revision-collision",
                  f"Published stages already live under {version_url}: "
                  f"{', '.join(stages)}.")


def check_filenames(items: dict[str, str], stage: str, f: Findings,
                    required: tuple[str, ...] = ("md", "html", "pdf")) -> str:
    """Delivery items must be <base>-<stage>.<ext>. Returns <base>-<stage>.
    `required` is the track's format set: (md, html, pdf) on the markdown
    track, (docx, html, pdf) on the DOCX-native track."""
    stems = {os.path.splitext(os.path.basename(p))[0] for p in items.values()}
    if len(stems) > 1:
        f.add(BLOCKER, "filenames", f"Delivery items do not share one basename: {sorted(stems)}")
    stem = sorted(stems)[0] if stems else ""
    for bad in ("draft", "tmp", "rc"):
        if re.search(rf"[-_.]{bad}\d*$", stem) or f"-{bad}-" in stem:
            f.add(BLOCKER, "filenames",
                  f"Delivery filename '{stem}' carries a working token ('{bad}'); files must be "
                  f"named for the stage being published (…-{stage}.md/.html/.pdf).")
    if stem and not stem.endswith(f"-{stage}"):
        f.add(BLOCKER, "filenames",
              f"Delivery filename '{stem}' does not end in '-{stage}' (the stage directory name).")
    missing = set(required) - set(items)
    if missing:
        f.add(BLOCKER, "filenames", f"Missing delivery format(s): {', '.join(sorted(missing))}")
    return stem


def check_front_matter(md_text: str, items: dict[str, str], version: str, stage: str,
                       f: Findings) -> str:
    """Validate This/Latest stage URL blocks. Returns the This-Stage base URL."""
    this_urls = stage_urls_from_md(md_text, "This")
    latest_urls = stage_urls_from_md(md_text, "Latest")
    base = ""
    if not this_urls:
        f.add(BLOCKER, "front-matter", "No 'This stage' URL block found in the markdown.")
    delivery_names = {os.path.basename(p) for p in items.values()}
    seen_ext = set()
    for u in this_urls + latest_urls:
        if not u.startswith(SITE + "/"):
            f.add(BLOCKER, "front-matter",
                  f"Stage URL is not under {SITE}: {u}")
    for u in this_urls:
        if f"/{version}/" not in u or f"/{stage}/" not in u:
            f.add(BLOCKER, "front-matter",
                  f"This-stage URL does not contain /{version}/ and /{stage}/: {u}")
        name = u.rstrip(".").rsplit("/", 1)[-1]
        if name not in delivery_names:
            f.add(BLOCKER, "front-matter",
                  f"This-stage URL points at '{name}' which is not a file in the package: {u}")
        else:
            seen_ext.add(os.path.splitext(name)[1].lstrip("."))
            base = u.rsplit("/", 1)[0] + "/"
    for ext in ("md", "html", "pdf"):
        if this_urls and ext not in seen_ext:
            f.add(WARN, "front-matter", f"This-stage block does not list the .{ext} artifact.")
    for u in latest_urls:
        if f"/{stage}/" in u:
            f.add(BLOCKER, "front-matter",
                  f"Latest-stage URL must point at the version root (no /{stage}/): {u}")
        if f"/{version}/" not in u:
            f.add(BLOCKER, "front-matter", f"Latest-stage URL not under /{version}/: {u}")
    # any other docs URL declaring a different version is a stale-draft tell,
    # except legitimate citations in the Previous-Stage / Related-Work blocks
    legit = set(stage_urls_from_md(md_text, "Previous"))
    rw = re.search(r"^#+ Related [Ww]ork.*?$(.*?)^#+ ", md_text, re.M | re.S)
    if rw:
        legit |= set(re.findall(r"https?://\S+?(?=[)\s\\]|$)", rw.group(1)))
    for u in set(re.findall(r"https?://docs\.oasis-open\.org/\S+", md_text)) - legit:
        m = re.search(r"/v(\d+\.\d+)/", u)
        if m and f"v{m.group(1)}" != version and "/templates/" not in u:
            f.add(WARN, "front-matter",
                  f"URL declares version v{m.group(1)} (package is {version}): {u.rstrip('.,)')}"
                  " -- confirm this is an intentional external reference.")
    return base


def check_residue(md_text: str, html_text: str, f: Findings) -> None:
    for label, text in (("markdown", strip_code_blocks(md_text, "md")),
                        ("html", strip_code_blocks(html_text, "html"))):
        for m in re.finditer(r"TODO\([^)]*\)|TODO:", text):
            f.add(BLOCKER, "residue", f"Editor TODO left in {label}: '{m.group(0)}'")
        for m in re.finditer(r"(?i)^\s*tbd\.?\s*$", text, re.M):
            f.add(BLOCKER, "residue", f"'tbd' placeholder section left in {label}.")
        if re.search(r"[Ww]ill be filled in", text):
            f.add(WARN, "residue",
                  f"'Will be filled in …' placeholder present in {label} (acceptable for an "
                  f"early stage; must be resolved before CS).")


def check_html(html_text: str, stem: str, f: Findings,
               anchor_severity: str = BLOCKER) -> None:
    """`anchor_severity` is BLOCKER on the markdown track (the author controls
    the source and must fix it) and WARN on the DOCX-native track (danglers
    there are source-DOCX artifacts: navigation-only, fix path is the TC's
    next revision, not the render)."""
    p = _AnchorParser()
    p.feed(html_text)
    title = " ".join(p.title.split())
    if re.search(r"(?i)[\s\-–—](tmp|draft|wip)$", title):
        f.add(BLOCKER, "html-title", f"HTML <title> carries working residue: '{title}'")
    if title and stem.split("-")[0].replace("_", " ") and len(title) < 8:
        f.add(WARN, "html-title", f"HTML <title> looks too short: '{title}'")
    # Absorbed from publisher-toolkit lint_html.py (the render-time D-series):
    # D2 pandoc title-block residue and D3 CI runner-path leaks arrive at
    # intake too, because TC repos run the same shared workflows.
    if re.search(r'<header\s+id="title-block-header"', html_text, re.I):
        f.add(BLOCKER, "html-residue",
              "Stale pandoc <header id=\"title-block-header\"> block: renders the "
              "title twice on the PDF cover (lint D2).")
    for m in sorted(set(re.findall(r'(?:href|src)="(/home/runner/[^"]*)"', html_text))):
        f.add(BLOCKER, "html-residue",
              f"CI runner path leaked into the HTML: {m} (lint D3).")
    if title:
        flat = re.sub(r"\s+", " ", html_text)
        h1s = re.findall(r"<h1\b[^>]*>(.*?)</h1>", flat, re.I | re.S)
        norm = lambda s: re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", s)).strip().lower()
        dup = sum(1 for h in h1s if norm(h) == title.lower())
        if dup > 1:
            f.add(BLOCKER, "html-residue",
                  f"Document title appears in {dup} <h1> elements; the PDF cover "
                  f"renders the title twice (lint D1).")
    missing = sorted({h for h in p.internal_hrefs if h not in p.ids})
    for h in missing[:20]:
        hint = (" (stale Word TOC field: the bookmark is absent from the source DOCX; "
                "regenerate the TOC in Word)") if h.startswith("_Toc") else ""
        f.add(anchor_severity, "html-anchors",
              f"Internal link '#{h}' has no matching anchor in the HTML.{hint}")
    if len(missing) > 20:
        f.add(anchor_severity, "html-anchors",
              f"...and {len(missing) - 20} more unresolved internal links.")
    if missing:
        f.add(INFO, "html-anchors",
              f"{len(missing)} of {len(set(p.internal_hrefs))} internal links unresolved.")
    if not p.internal_hrefs:
        f.add(WARN, "html-anchors", "HTML contains no internal (fragment) links at all; "
                                    "expected a linked Table of Contents.")


def check_md_links(md_text: str, f: Findings) -> None:
    md_text = strip_code_blocks(md_text, "md")
    for m in re.finditer(r"\[<?(\S+?)>?\]\((\S+?)\)", md_text):
        if m.group(1) == m.group(2) and m.group(1).startswith("http"):
            f.add(WARN, "md-links",
                  f"Dual link [url](url) — prefer a bare URL (autolinked) or real anchor text: "
                  f"{m.group(2)}")
    for i, line in enumerate(md_text.splitlines(), 1):
        if re.search(r"https?://\S+\.\\$", line):
            f.add(BLOCKER, "md-links",
                  f"Line {i}: bare URL runs into '.\\' with no space; pandoc autolink pulls the "
                  f"period and backslash into the href and eats the line break. Use '. \\'.")


def check_md_fences(md_text: str, f: Findings) -> None:
    """Absorbed from publisher-toolkit preprocess_md.py (lint D6): an opening
    code fence whose info string carries trailing text (``` yaml <!-- note -->)
    is not recognized as a fence by pandoc's classic fenced_code_blocks -- the
    whole block collapses to inline code and loses its formatting. Shipped
    once (DPS prov-meta, 28 yaml blocks, May 2026; editor-flagged blocker).
    The curly-attribute form (```{.lang title="x"}) is fine."""
    in_fence = False
    delim = ""
    for i, line in enumerate(md_text.splitlines(), 1):
        m = re.match(r"^(\s{0,3})(`{3,}|~{3,})(.*)$", line)
        if not m:
            continue
        marker, info = m.group(2), m.group(3).strip()
        if in_fence:
            if marker[0] == delim and not info:
                in_fence = False
            continue
        in_fence = True
        delim = marker[0]
        if info and not info.startswith("{") and re.match(r"^[\w+-]+\s+\S", info):
            f.add(BLOCKER, "fence-collapse",
                  f"Line {i}: opening fence info string carries trailing text "
                  f"('{info[:40]}...'): pandoc does not recognize it as a fence and "
                  f"the block collapses to inline code. Use ```{{.lang title=\"...\"}} "
                  f"or drop the trailing text.")


IMG_EXTS = {".svg", ".png", ".jpg", ".jpeg", ".gif", ".webp"}


def check_image_policy(stage_dir: str, html_text: str, f: Findings) -> None:
    """Absorbed from publisher-toolkit inline_images.py (lint D7). Two halves:
    HTML constructs the publication pipeline refuses (empty/absolute/traversal
    src, srcset, <picture>), and image-file safety -- an SVG carrying <script>,
    event handlers, or external refs is active content on docs.oasis-open.org.
    Size caps mirror the inliner's policy (warn 500KB, refuse 2MB, 5MB total)."""
    flat = (html_text or "").replace("\r", "").replace("\n", "")
    for m in re.finditer(r'<img\b[^>]*>', flat, re.I):
        tag = m.group(0)
        src_m = re.search(r'src="([^"]*)"', tag)
        src = src_m.group(1).strip() if src_m else ""
        if src_m and not src:
            f.add(BLOCKER, "image-policy", "Empty <img src> in the HTML.")
        elif src.startswith("/") and not src.startswith("//"):
            f.add(BLOCKER, "image-policy",
                  f"Absolute-path <img src=\"{src[:60]}\">: resolves outside the "
                  f"package on publication.")
        elif ".." in src.split("?")[0].split("/"):
            f.add(BLOCKER, "image-policy",
                  f"Path-traversal <img src=\"{src[:60]}\">: escapes the package.")
        if "srcset=" in tag.lower():
            f.add(WARN, "image-policy",
                  "<img srcset> present: the publication pipeline refuses "
                  "responsive-image constructs (self-containment policy).")
    if re.search(r"<picture\b", flat, re.I):
        f.add(WARN, "image-policy",
              "<picture> element present: the publication pipeline refuses it "
              "(self-containment policy).")
    total = 0
    for root, _dirs, files in os.walk(stage_dir):
        for name in files:
            ext = os.path.splitext(name)[1].lower()
            if ext not in IMG_EXTS:
                continue
            p = os.path.join(root, name)
            rel = os.path.relpath(p, stage_dir)
            size = os.path.getsize(p)
            total += size
            if size > 2_097_152:
                f.add(WARN, "image-policy",
                      f"{rel}: {size // 1024}KB exceeds the pipeline's 2MB "
                      f"per-image refusal cap.")
            if ext == ".svg":
                try:
                    body = open(p, encoding="utf-8", errors="replace").read()
                except OSError:
                    continue
                if re.search(r"<script\b", body, re.I):
                    f.add(BLOCKER, "image-policy",
                          f"{rel}: SVG contains <script> -- active content is "
                          f"refused on docs.oasis-open.org.")
                if re.search(r"\son\w+\s*=", body, re.I):
                    f.add(BLOCKER, "image-policy",
                          f"{rel}: SVG carries inline event handlers (on*=) -- "
                          f"active content is refused.")
                if re.search(r"<(image|use)\b[^>]*href=\"https?://", body, re.I):
                    f.add(BLOCKER, "image-policy",
                          f"{rel}: SVG references an external image/use target; "
                          f"the published artifact would not be self-contained.")
    if total > 5_242_880:
        f.add(WARN, "image-policy",
              f"Cumulative image payload {total // 1_048_576}MB exceeds the "
              f"pipeline's 5MB inlining cap.")


def check_pdf_cover(pdf_path: str, title: str, f: Findings) -> None:
    """Absorbed from publisher-toolkit step_2_convert_html_to_pdf.py: A1 (the
    document title must appear exactly once on the PDF cover page -- twice
    means stale pandoc header residue baked into the render; shipped on DPS
    May 2026) and A2 (no /home/runner CI path anywhere in the PDF text)."""
    pdftotext = shutil.which("pdftotext")
    if not pdftotext or not title or title == "-":
        return
    try:
        page1 = subprocess.run([pdftotext, "-l", "1", pdf_path, "-"],
                               capture_output=True, text=True, timeout=60).stdout
        full = subprocess.run([pdftotext, pdf_path, "-"],
                              capture_output=True, text=True, timeout=120).stdout
    except Exception:  # noqa: BLE001 - pdf-sync already reports readability
        return
    norm = re.sub(r"\s+", " ", title.lower())
    count = re.sub(r"\s+", " ", page1.lower()).count(norm)
    if count > 1:
        f.add(BLOCKER, "pdf-cover",
              f"Document title appears {count} times on the PDF cover page "
              f"(stale title-block residue baked into the render).")
    if "/home/runner/" in full:
        f.add(BLOCKER, "pdf-cover",
              "CI runner path (/home/runner/) leaked into the rendered PDF text.")


def check_schemas(stage_dir: str, base_this_stage: str, version: str, stage: str,
                  f: Findings) -> None:
    if not base_this_stage:
        return
    # $id convention: schemas identify at the version root (latest), not the stage path
    latest_root = base_this_stage.replace(f"/{stage}/", "/")
    for root, _dirs, files in os.walk(stage_dir):
        for name in files:
            if not name.endswith(".json"):
                continue
            path = os.path.join(root, name)
            try:
                doc = json.loads(read_text(path))
            except json.JSONDecodeError as e:
                f.add(BLOCKER, "schema-id", f"{name}: not valid JSON ({e})")
                continue
            if not isinstance(doc, dict) or "$id" not in doc:
                continue
            rel = os.path.relpath(path, stage_dir)
            expected = latest_root + rel.replace(os.sep, "/")
            declared = doc["$id"]
            if declared != expected:
                roots = {latest_root, re.sub(r"errata\d+/$", "", latest_root)}
                same_root = any(declared.startswith(r) for r in roots)
                same_name = declared.rsplit("/", 1)[-1] == name
                if same_root and same_name:
                    f.add(WARN, "schema-id",
                          f"{rel}: $id is '{declared}', a flattened path under the version "
                          f"root (CSAF v2.0 publishes this way). Confirm a copy publishes "
                          f"at the $id location, or align $id with '{expected}'.")
                else:
                    f.add(BLOCKER, "schema-id",
                          f"{rel}: $id is '{declared}' but the file publishes under "
                          f"'{latest_root}'. An implementer following the $id gets a 404 "
                          f"or the wrong document.")
            # any self-referencing const inside the schema must agree with $id
            blob = json.dumps(doc)
            for u in set(re.findall(r"https://docs\.oasis-open\.org/[^\"\s]+\.json", blob)):
                if u.rsplit("/", 1)[-1] == name and u != declared and u != expected:
                    f.add(BLOCKER, "schema-id",
                          f"{rel}: internal reference '{u}' disagrees with $id '{declared}'.")


def check_pdf(pdf_path: str, this_urls_base: str, version: str, f: Findings) -> None:
    pdftotext = shutil.which("pdftotext")
    if not pdftotext:
        f.add(WARN, "pdf-sync", "pdftotext not on PATH: the PDF front-matter cross-check was "
                                "SKIPPED. The intake side will run it; install poppler to run "
                                "it here.")
        return
    try:
        proc = subprocess.run([pdftotext, "-l", "3", pdf_path, "-"],
                              capture_output=True, text=True, timeout=60)
    except Exception as e:  # noqa: BLE001 - report, do not crash the gate
        f.add(WARN, "pdf-sync", f"pdftotext failed: {e}")
        return
    if proc.returncode != 0:
        f.add(BLOCKER, "pdf-sync",
              f"pdftotext could not read the PDF (exit {proc.returncode}): "
              f"{proc.stderr.strip()[:200]}")
        return
    txt = proc.stdout
    if this_urls_base and this_urls_base not in txt.replace("\n", ""):
        f.add(BLOCKER, "pdf-sync",
              f"PDF front matter does not contain the canonical this-stage base URL "
              f"({this_urls_base}); the PDF was likely rendered from an older draft.")
    # a different version of THIS spec in the PDF is suspicious (previous-stage
    # citations are expected, so this stays a warning)
    spec_base = ""
    if this_urls_base:
        spec_base = this_urls_base.split(f"/{version}/", 1)[0]
    if spec_base:
        for m in set(re.findall(re.escape(spec_base) + r"/v(\d+\.\d+)/", txt)):
            if f"v{m}" != version:
                f.add(WARN, "pdf-sync",
                      f"PDF cites {spec_base}/v{m}/ (package is {version}); expected only "
                      f"as a previous-stage reference -- confirm.")


# Template front-matter sections, in canonical order. (label, pattern, required)
TEMPLATE_SECTIONS = [
    ("This stage/version", r"This (Stage|Version)", True),
    ("Previous stage/version", r"Previous (Stage|Version)", True),
    ("Latest stage/version", r"Latest (Stage|Version)", True),
    ("Technical Committee", r"Technical Committee", True),
    ("Chair(s)", r"Chairs?\b", True),
    ("Editor(s)", r"Editors?\b", True),
    ("Abstract", r"Abstract", True),
    ("Status", r"(Document )?Status", False),
    ("Citation format", r"Citation", False),
    ("Notices", r"Notices|License, Document Status", False),
]


def check_template(md_text: str, html_text: str, f: Findings) -> None:
    """Template structure per the OASIS spec template and TC Process:
    front-matter section order, mandatory Conformance section, stylesheet."""
    positions = []
    for label, pat, required in TEMPLATE_SECTIONS:
        m = re.search(rf"^#+\s+{pat}", md_text, re.M | re.I)
        if not m:
            if required:
                f.add(BLOCKER, "template",
                      f"Required front-matter section missing: {label}.")
        else:
            positions.append((m.start(), label))
    if positions != sorted(positions):
        order = " -> ".join(lbl for _pos, lbl in positions)
        f.add(WARN, "template",
              f"Front-matter sections out of template order: {order}.")

    # TC Process: every Standards Track Work Product carries a Conformance section
    if not re.search(r"^#+\s+[\d.\sA-Za-z]*Conformance", md_text, re.M | re.I):
        f.add(BLOCKER, "template",
              "No Conformance section found. The TC Process requires a conformance "
              "clauses section in every Standards Track Work Product.")

    # Stylesheet adherence: the HTML should carry the OASIS look. Canonical is the
    # markdown-styles CSS from docs.oasis-open.org (linked or localized); a spec
    # shipping its own CSS is accepted practice but must be a conscious choice.
    if html_text:
        links = re.findall(r"<link[^>]+rel=[\"']?stylesheet[\"']?[^>]*>", html_text, re.I)
        hrefs = " ".join(links)
        inline_css = re.findall(r"<style\b", html_text, re.I)
        if re.search(r"markdown-styles[^\"']*\.css", hrefs):
            pass  # canonical stylesheet
        elif links or inline_css:
            body_font = ""
            m = re.search(r"font-family\s*:\s*([^;}}]+)", html_text, re.I)
            if m:
                body_font = m.group(1).strip()
            if body_font and not re.search(r"(?i)liberation|arial|helvetica", body_font):
                f.add(WARN, "template-css",
                      f"HTML does not use the canonical OASIS stylesheet and its primary "
                      f"font-family is '{body_font}'; the template look is Liberation "
                      f"Sans / Arial. Confirm the deviation is intentional.")
            else:
                f.add(INFO, "template-css",
                      "HTML ships its own stylesheet rather than the canonical "
                      "markdown-styles CSS; fonts match the template family. Accepted "
                      "practice (OpenEoX publishes this way), noting it for the record.")
        else:
            f.add(BLOCKER, "template-css",
                  "HTML carries no stylesheet at all (no <link rel=stylesheet>, no "
                  "<style> block).")


def check_correction_classes(md_text: str, stage_dir: str, base: str, stage: str,
                             f: Findings) -> None:
    """Defect classes from historical publication correction rounds
    (prov-meta May 2026, DMLex Jun 2026, UBL Aug 2025)."""
    prose = strip_code_blocks(md_text, "md")

    # DMLex class: files the spec cites under its own stage path must ship
    if base:
        for u in set(re.findall(re.escape(base) + r"[\w./%-]+", prose)):
            rel = u[len(base):].rstrip(".,)\\")
            if rel and not rel.endswith((".md", ".html", ".pdf")):
                if not os.path.isfile(os.path.join(stage_dir, rel)):
                    f.add(BLOCKER, "package-refs",
                          f"The document cites {u} under its own stage path, but "
                          f"'{rel}' is not in the package: it will 404 on publication.")

    # prov-meta class: visible URL and link target disagree (rename artifacts)
    for m in re.finditer(r"\[(https?://[^\]\s]+)\]\((https?://[^)\s]+)\)", prose):
        shown, target = m.group(1).rstrip("/"), m.group(2).rstrip("/")
        if shown != target:
            f.add(BLOCKER, "link-mismatch",
                  f"Visible URL and link target disagree: text shows '{m.group(1)}' but "
                  f"links to '{m.group(2)}'. One of them is wrong.")

    # prov-meta class: double slash in a relative path (Cloudflare 404s it)
    for m in set(re.findall(r"\]\((\.?/[^)\s]*//[^)\s]*)\)", prose)):
        f.add(BLOCKER, "double-slash",
              f"Relative path contains a double slash: '{m}'. Browsers tolerate it; the "
              f"CDN returns 404.")

    # prov-meta class: horizontal rule between logo and title becomes a PDF
    # page break in the publication CSS (blank first page)
    head = md_text[:600]
    if re.search(r"OASISLogo[^\n]*\)\s*\n+\s*(-{3,}|\*{3,}|_{3,})\s*\n", head):
        f.add(WARN, "cover-hr",
              "Horizontal rule between the OASIS logo and the title: the publication "
              "CSS treats <hr/> as a page break, which opens the PDF with a blank page. "
              "Harmless in other renderers; remove if publishing through the OASIS "
              "HTML-to-PDF path.")

    # prov-meta class: a 'Latest'-labelled URL for THIS spec carrying the
    # stage segment (must be the persistent version-root path)
    spec_base = base.split(f"/{stage}/", 1)[0] + "/" if base and f"/{stage}/" in base else ""
    if spec_base:
        for line in prose.splitlines():
            if not re.match(r"\s*(?:[*+-]\s*)?Latest[\w /]*:", line, re.I):
                continue
            for u in re.findall(r"https?://docs\.oasis-open\.org/\S+", line):
                if u.startswith(spec_base) and f"/{stage}/" in u:
                    f.add(BLOCKER, "front-matter",
                          f"'Latest'-labelled URL carries the stage segment /{stage}/ "
                          f"(should be the persistent version-root path): {u.rstrip('.,)')}")


def check_pdf_fonts(stage_dir: str, pdf_path: str, html_text: str, f: Findings) -> None:
    """The PDF's embedded fonts should match the font families the package's own
    CSS declares (the CSS is the typography authority for a publication).
    Divergence is a finding, not a blocker: render class is judged against the
    TC's precedent. Soft-degrades when poppler's pdffonts is absent, and skips
    when the package declares no font authority of its own."""
    declared_src = html_text or ""
    for root, _dirs, files in os.walk(stage_dir):
        for name in files:
            if name.endswith(".css"):
                declared_src += read_text(os.path.join(root, name))
    families = set()
    for decl in re.findall(r"font-family\s*:\s*([^;}}\n\"]+)", declared_src, re.I):
        for fam in decl.split(","):
            fam = fam.strip().strip("'\"").lower()
            if fam and fam not in {"serif", "sans-serif", "monospace", "cursive",
                                   "fantasy", "system-ui", "inherit"}:
                families.add(re.sub(r"[\s_-]", "", fam))
    if not families:
        f.add(INFO, "pdf-fonts", "Package declares no local font authority (no "
                                 "font-family in its HTML/CSS); font check skipped.")
        return
    pdffonts = shutil.which("pdffonts")
    if not pdffonts:
        f.add(INFO, "pdf-fonts", "pdffonts (poppler) not on PATH; embedded-font "
                                 "check skipped. The intake side runs it.")
        return
    try:
        proc = subprocess.run([pdffonts, pdf_path], capture_output=True, text=True,
                              timeout=60)
    except Exception as e:  # noqa: BLE001
        f.add(WARN, "pdf-fonts", f"pdffonts failed: {e}")
        return
    embedded = set()
    for line in proc.stdout.splitlines()[2:]:
        name = line.split()[0] if line.split() else ""
        if not name or name == "[none]":
            continue
        name = re.sub(r"^[A-Z]{6}\+", "", name)
        base = re.split(r"[-,]", name)[0]
        if base:
            embedded.add(base)
    stray = sorted(b for b in embedded
                   if not any(fam in b.lower().replace(" ", "") or
                              b.lower().replace(" ", "") in fam for fam in families))
    if stray:
        f.add(WARN, "pdf-fonts",
              f"PDF embeds fonts not declared by the package's own CSS: "
              f"{', '.join(stray)}. The CSS declares: {', '.join(sorted(families))}. "
              f"Confirm the divergence is intentional (pdffonts <file.pdf> re-checks "
              f"this after a toolchain change).")


def check_manifest(stage_dir: str, f: Findings) -> None:
    mpath = os.path.join(stage_dir, "manifest.json")
    if not os.path.exists(mpath):
        f.add(INFO, "manifest", "No manifest.json in the package. Emit one (--emit-manifest or "
                                "your own tool) and intake verification becomes automatic.")
        return
    try:
        man = json.loads(read_text(mpath))
    except json.JSONDecodeError as e:
        f.add(BLOCKER, "manifest", f"manifest.json is not valid JSON: {e}")
        return
    for item in man.get("items", []):
        p = os.path.join(stage_dir, item.get("path", ""))
        if not os.path.isfile(p):
            f.add(BLOCKER, "manifest", f"manifest lists missing file: {item.get('path')}")
            continue
        actual = sha256_file(p)
        if actual != item.get("sha256"):
            f.add(BLOCKER, "manifest",
                  f"sha256 mismatch for {item['path']}: manifest {item.get('sha256')}, "
                  f"file {actual}")


def emit_manifest(stage_dir: str, version: str, stage: str) -> str:
    items = []
    for root, _dirs, files in os.walk(stage_dir):
        for name in sorted(files):
            if name == "manifest.json":
                continue
            p = os.path.join(root, name)
            rel = os.path.relpath(p, stage_dir).replace(os.sep, "/")
            ext = os.path.splitext(name)[1].lstrip(".").lower()
            role = {"md": "authoritative", "html": "delivery", "pdf": "delivery",
                    "json": "schema"}.get(ext, "other")
            items.append({"path": rel, "role": role, "sha256": sha256_file(p),
                          "bytes": os.path.getsize(p)})
    commit = os.environ.get("GITHUB_SHA", "")
    if not commit:
        try:
            commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                                    text=True, cwd=stage_dir, timeout=10).stdout.strip()
        except Exception:  # noqa: BLE001
            commit = ""
    tools = {}
    for tool in ("pandoc", "typst", "tidy"):
        exe = shutil.which(tool)
        if exe:
            try:
                v = subprocess.run([exe, "--version"], capture_output=True, text=True,
                                   timeout=10).stdout.splitlines()[0]
                tools[tool] = v
            except Exception:  # noqa: BLE001
                pass
    man = {"version": version, "stage": stage, "source": {"commit": commit},
           "tools": tools, "items": items}
    out = os.path.join(stage_dir, "manifest.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(man, fh, indent=2)
        fh.write("\n")
    return out


JUNK_NAMES = {".DS_Store", "Thumbs.db", "desktop.ini"}
JUNK_DIRS = {"__MACOSX", ".git", ".venv", "venv", "node_modules"}


def check_hygiene(stage_dir: str, f: Findings, delivery_names: set | None = None) -> None:
    """OS junk and case problems. The publication origin is case-sensitive:
    a mixed-case filename means every lowercase citation of it 404s."""
    delivery_names = delivery_names or set()
    for root, dirs, files in os.walk(stage_dir):
        # Self/parent-referential symlinks materialize into unbounded directory
        # recursion on deploy (rsync -L, s3 sync --follow-symlinks): KMIP
        # Profiles v3.0 csd01 shipped 41 nested levels (4,095 junk objects)
        # from a single 'kmip-v3.0 -> .' (found 15 Jul 2026).
        for name in list(dirs) + files:
            p = os.path.join(root, name)
            if os.path.islink(p):
                tgt = os.path.realpath(p)
                here = os.path.realpath(root)
                if tgt == here or here.startswith(tgt + os.sep):
                    rel = os.path.relpath(p, stage_dir)
                    f.add(BLOCKER, "symlinks",
                          f"Symlink '{rel}' points at its own ancestor "
                          f"('{os.readlink(p)}'): deploys materialize symlinks, so this "
                          f"expands into unbounded directory recursion on the CDN origin.")
        for d in list(dirs):
            if d in JUNK_DIRS:
                f.add(BLOCKER, "junk-files",
                      f"Working directory '{d}/' inside the package; remove before submitting.")
                dirs.remove(d)
        for name in files:
            if name in JUNK_NAMES or name.endswith(("~", ".bak", ".orig", ".swp")):
                f.add(BLOCKER, "junk-files",
                      f"Junk file in package: {os.path.relpath(os.path.join(root, name), stage_dir)}")
            elif name != name.lower() and name != "OASISLogo-v3.0.png":
                rel = os.path.relpath(os.path.join(root, name), stage_dir)
                sev = BLOCKER if name in delivery_names else WARN
                f.add(sev, "case",
                      f"Mixed-case filename '{rel}': the publication host is case-sensitive "
                      f"and canonical paths are lowercase; lowercase citations of this file "
                      f"will 404." + ("" if sev == BLOCKER else " (auxiliary file: warning; "
                      "published precedent exists, e.g. -DIFF.pdf)"))


def check_policy(md_text: str, html_text: str, version: str, stage: str,
                 f: Findings) -> None:
    """TC Handbook / template conventions that repeatedly bounce submissions."""
    prose = strip_code_blocks(md_text, "md")

    # dead mailing-list infrastructure: mail to lists.oasis-open.org silently fails
    for m in sorted(set(re.findall(r"[\w.+-]+@lists\.oasis-open\.org", prose))):
        f.add(BLOCKER, "dead-lists",
              f"References mailing address '{m}': lists.oasis-open.org no longer accepts "
              f"mail (messages fail silently). Point comments at the TC's Higher Logic "
              f"comment facility instead.")
    if "lists.oasis-open.org/archives" in prose:
        f.add(WARN, "dead-lists",
              "Links into lists.oasis-open.org/archives: verify each archive link still "
              "resolves; the list infrastructure is being retired.")

    # normative keywords demand the keyword references
    if re.search(r"\b(MUST NOT|MUST|SHALL NOT|SHALL|SHOULD NOT|SHOULD|MAY|"
                 r"REQUIRED|RECOMMENDED|OPTIONAL)\b", prose):
        if not re.search(r"RFC\s?2119", md_text):
            f.add(BLOCKER, "rfc-keywords",
                  "Document uses normative key words but does not cite RFC 2119 in its "
                  "references / key-words section.")
        elif not re.search(r"RFC\s?8174", md_text):
            f.add(WARN, "rfc-keywords",
                  "RFC 2119 is cited but RFC 8174 (uppercase-only clarification) is not; "
                  "the current template cites both.")

    # canonical logo
    for m in set(re.findall(r"!\[[^\]]*\]\((\S*?[Ll]ogo\S*?)\)", md_text)):
        if m != "https://docs.oasis-open.org/templates/OASISLogo-v3.0.png":
            f.add(WARN, "logo",
                  f"Logo source '{m}' is not the canonical "
                  f"https://docs.oasis-open.org/templates/OASISLogo-v3.0.png")

    # previous stage: anything past 01 must cite its predecessor
    m = re.fullmatch(r"([a-z]+)(\d\d)", stage)
    if m and int(m.group(2)) > 1:
        prev = stage_urls_from_md(md_text, "Previous")
        if not any("docs.oasis-open.org" in u for u in prev):
            f.add(BLOCKER, "previous-stage",
                  f"Stage {stage} must cite its previous stage URLs; the Previous-Stage "
                  f"block is empty or N/A.")

    # date agreement between md and html front matter, and copyright year
    md_date = re.search(r"^#+\s+(\d{1,2} \w+ \d{4})\s*$", md_text, re.M)
    if md_date:
        if html_text and md_date.group(1) not in html_text:
            f.add(BLOCKER, "date-sync",
                  f"Front-matter date '{md_date.group(1)}' from the markdown does not "
                  f"appear in the HTML; the HTML was rendered from a different revision.")
        year = md_date.group(1).rsplit(" ", 1)[-1]
        cr = re.search(r"Copyright\s+©?\s*OASIS Open\s+(\d{4})", md_text)
        if cr and cr.group(1) != year:
            f.add(WARN, "date-sync",
                  f"Copyright year {cr.group(1)} does not match the document date year "
                  f"{year}.")

    # self-referential URLs must be lowercase (case-sensitive origin)
    for u in set(re.findall(r"https://docs\.oasis-open\.org/\S+", prose)):
        path = u.split("docs.oasis-open.org/", 1)[1].rstrip(".,)\\")
        if path != path.lower() and "/templates/" not in u:
            f.add(WARN, "case",
                  f"Mixed-case path in docs.oasis-open.org URL (host is case-sensitive): {u}")


# ------------------------------------------------- DOCX-native track checks
#
# KMIP/PKCS#11-style packages: the TC's .docx is authoritative and the
# HTML/PDF are Microsoft Word renders. The markdown-track checks do not apply
# (there is no .md by design), but the format-agnostic ones do, plus a set of
# render-fidelity checks specific to the track. Provenance: the 15 Jul 2026
# KMIP v3.0 csd02 audit, where the anchor check found three dangling bookmarks
# that two human audit passes had left unvalidated, and the same day's csd01
# symlink-recursion cleanup.

def check_generator_meta(html_text: str, f: Findings) -> None:
    """DOCX-native renders must come from Microsoft Word. A LibreOffice or
    other render differs in kind from the TC's precedent (styling, size,
    metadata) and is a re-do, not a publication (KMIP csprd01, Jul 2026)."""
    m = re.search(r'<meta\s+name="?Generator"?\s+content="([^"]+)"', html_text, re.I)
    gen = m.group(1) if m else ""
    if "Microsoft Word" not in gen:
        f.add(BLOCKER, "generator",
              f"HTML Generator is '{gen or 'absent'}'; a DOCX-native render must be "
              f"produced by Microsoft Word to match the TC's publication precedent.")


def check_vml_fallback(html_text: str, f: Findings) -> None:
    """A VML-only image is invisible in every modern browser. Word exports it
    when the source DOCX carries 'rely on VML'; each v:imagedata needs a
    paired <![if !vml]><img> fallback. Shipped live twice before this check
    (PKCS#11 v3.2 os cover, KMIP v3.0 csd01 cover)."""
    flat = html_text.replace("\r", "").replace("\n", " ")
    vml = len(re.findall(r"<v:imagedata\b", flat))
    fallbacks = len(re.findall(r"<!\[if !vml\]>\s*<img\b", flat))
    if vml and fallbacks < vml:
        f.add(BLOCKER, "vml-fallback",
              f"{vml} VML image(s) but only {fallbacks} <![if !vml]><img> fallback(s): "
              f"browsers that ignore VML show nothing (the invisible-cover-logo class). "
              f"Clear the source DOCX's relyOnVML web option and re-export.")


def check_asset_refs(stage_dir: str, html_path: str, html_text: str,
                     f: Findings) -> None:
    """Every relative src/href the HTML references must ship in the package.
    Image refs escape link-only sweeps (a DMLex diagram 404'd for 14 months
    this way); Word wraps attribute values across lines, so flatten first."""
    flat = html_text.replace("\r", "").replace("\n", "")
    refs = set(re.findall(r'(?:src|href)="([^"#]+)"', flat))
    base = os.path.dirname(os.path.abspath(html_path))
    missing = []
    for r in sorted(refs):
        # any URI scheme (https, ftp, mailto, data, ...) is external, not a
        # package-relative ref (ftp:// RFC citations false-fired before this)
        if re.match(r"(?i)[a-z][a-z0-9+.-]*:|//", r):
            continue
        target = os.path.normpath(os.path.join(base, r.split("?")[0]))
        if not os.path.exists(target):
            missing.append(r)
    for r in missing[:20]:
        f.add(BLOCKER, "asset-refs",
              f"HTML references '{r}' which is not in the package; it 404s on "
              f"publication.")
    if len(missing) > 20:
        f.add(BLOCKER, "asset-refs", f"...and {len(missing) - 20} more missing asset refs.")


def check_html_cover(html_text: str, version: str, stage: str,
                     f: Findings) -> str:
    """Front-matter blocks parsed from the rendered HTML cover: the DOCX-native
    equivalent of the markdown front-matter checks. Returns the this-stage
    base URL for the PDF cross-check."""
    # Word front-loads hundreds of KB of styles/xml; the cover starts at <body>
    body_at = html_text.find("<body")
    cover = html_text[body_at if body_at >= 0 else 0:][:120000]
    head = re.sub(r"<[^>]+>", " ", cover)
    head = re.sub(r"&nbsp;|&#160;|\s+", " ", head)

    def urls_between(start: str, ends: list[str]) -> list[str] | None:
        m = re.search(start, head, re.I)
        if not m:
            return None
        seg = head[m.end():]
        cut = len(seg)
        for e in ends:
            m2 = re.search(e, seg, re.I)
            if m2:
                cut = min(cut, m2.start())
        return re.findall(r"https?://docs\.oasis-open\.org/[^\s\"<>]+", seg[:cut])

    this_urls = urls_between(r"This (version|stage)",
                             [r"Previous (version|stage)", r"Latest (version|stage)",
                              r"Technical Committee"])
    prev_urls = urls_between(r"Previous (version|stage)",
                             [r"Latest (version|stage)", r"Technical Committee"])
    latest_urls = urls_between(r"Latest (version|stage)",
                               [r"Technical Committee", r"Chairs?\b"])
    base = ""
    if this_urls is None or not this_urls:
        f.add(BLOCKER, "front-matter",
              "No 'This version' URL block found on the HTML cover.")
    else:
        for u in this_urls:
            if f"/{version}/" not in u or f"/{stage}/" not in u:
                f.add(BLOCKER, "front-matter",
                      f"This-version URL does not contain /{version}/ and /{stage}/: {u}")
            else:
                base = u.rsplit("/", 1)[0] + "/"
    for u in latest_urls or []:
        if f"/{stage}/" in u:
            f.add(BLOCKER, "front-matter",
                  f"Latest-version URL must point at the version root (no /{stage}/): {u}")
    m = re.fullmatch(r"([a-z]+)(\d\d)", stage)
    if m and int(m.group(2)) > 1 and not (prev_urls or []):
        f.add(BLOCKER, "previous-stage",
              f"Stage {stage} must cite its previous stage URLs; no Previous-version "
              f"block with docs.oasis-open.org URLs found on the HTML cover.")
    return base


def _first_h1(md_text: str) -> str:
    for line in md_text.splitlines():
        if line.startswith("# "):
            return line.strip("# ").strip()
    return ""


def run(stage_dir: str, f: Findings) -> None:
    """Output-centric validation. All roads lead to HTML and PDF: whatever the
    authoring format (Markdown, Word, DocBook/XML, LaTeX, ...), the published
    form is HTML + PDF at the canonical URLs, so the bulk of the gate runs on
    those outputs for every package. Source-format checks are add-ons applied
    to whatever source the package carries."""
    version, stage = parse_stage(stage_dir)
    check_stage_name(stage, f)
    items = find_delivery_items(stage_dir, ("md", "docx", "html", "pdf"))
    if not items:
        f.add(BLOCKER, "filenames", f"No delivery items found in {stage_dir}")
        return

    md_text = read_text(items["md"]) if "md" in items else ""
    html_text = read_text(items["html"]) if "html" in items else ""
    is_word = "docx" in items and "md" not in items

    # ---- the bar: HTML + PDF, always -------------------------------------
    required = ["html", "pdf"]
    if "md" in items:
        required.append("md")        # md-track contract preserves the source
    elif "docx" in items:
        required.append("docx")      # Word-track contract preserves the source
    stem = check_filenames(items, stage, f, required=tuple(required))
    check_version_naming(version, stem, f)
    if "md" not in items and "docx" not in items and "html" in items:
        f.add(WARN, "filenames",
              "No authoritative source artifact (md/docx) in the package root; "
              "DocBook/XML and LaTeX sources should travel with their renderings.")
    if is_word:
        f.add(INFO, "track",
              "Word-authored package (authoritative .docx, no .md): source "
              "add-ons swapped for Word render-fidelity checks.")

    # ---- output suite: HTML ----------------------------------------------
    base = ""
    if md_text:
        base = check_front_matter(md_text, items, version, stage, f)
    if html_text:
        # anchors are source-side artifacts on Word renders: WARN there
        check_html(html_text, stem, f,
                   anchor_severity=WARN if is_word else BLOCKER)
        if not md_text:
            # no markdown front matter to read: parse the rendered cover,
            # which every publication carries regardless of authoring format
            base = check_html_cover(html_text, version, stage, f)
        if is_word:
            check_generator_meta(html_text, f)
        check_vml_fallback(html_text, f)
        check_asset_refs(stage_dir, items["html"], html_text, f)
        if not md_text:
            prose = re.sub(r"<[^>]+>", " ", strip_code_blocks(html_text, "html"))
            for m in sorted(set(re.findall(r"[\w.+-]+@lists\.oasis-open\.org", prose))):
                f.add(BLOCKER, "dead-lists",
                      f"References mailing address '{m}': lists.oasis-open.org no longer "
                      f"accepts mail (messages fail silently). Point comments at the TC's "
                      f"Higher Logic comment facility instead.")
            for u in set(re.findall(r"https://docs\.oasis-open\.org/\S+", prose)):
                path = u.split("docs.oasis-open.org/", 1)[1].rstrip(".,)\\")
                if path != path.lower() and "/templates/" not in u:
                    f.add(WARN, "case",
                          f"Mixed-case path in docs.oasis-open.org URL (host is "
                          f"case-sensitive): {u}")
    check_revision_collision(base, version, stage, f)
    check_residue(md_text, html_text, f)
    check_image_policy(stage_dir, html_text, f)

    # ---- output suite: PDF -----------------------------------------------
    if "pdf" in items:
        check_pdf(items["pdf"], base, version, f)
        title = _first_h1(md_text)
        if not title and html_text:
            tm = re.search(r"<title>(.*?)</title>", html_text, re.I | re.S)
            title = re.sub(r"\s+", " ", tm.group(1)).strip() if tm else ""
        check_pdf_cover(items["pdf"], title, f)
        check_pdf_fonts(stage_dir, items["pdf"], html_text, f)

    # ---- source add-ons ---------------------------------------------------
    if md_text:
        check_md_links(md_text, f)
        check_md_fences(md_text, f)
        check_policy(md_text, html_text, version, stage, f)
        check_template(md_text, html_text, f)
        check_correction_classes(md_text, stage_dir, base, stage, f)

    # ---- package suite ----------------------------------------------------
    check_schemas(stage_dir, base, version, stage, f)
    check_hygiene(stage_dir, f, {os.path.basename(p) for p in items.values()})
    check_manifest(stage_dir, f)


def locate_stage_dir(root: str) -> str:
    """Inside an extracted zip, find the deepest dir holding the delivery items."""
    for dirpath, _dirs, files in os.walk(root):
        exts = {os.path.splitext(n)[1].lstrip(".").lower() for n in files}
        if {"md", "html"} <= exts:
            return dirpath
    return root


def list_checks() -> int:
    """Self-introspect: parse this file's AST and count every individual
    defect condition (each BLOCKER/WARN finding site; continuation lines and
    INFO notes excluded). The advertised numbers are asserted from the code,
    never hand-counted in prose -- prose drifts, the AST does not."""
    import ast as _ast
    from collections import Counter
    tree = _ast.parse(open(os.path.abspath(__file__), encoding="utf-8").read())
    per_class: Counter = Counter()
    for node in _ast.walk(tree):
        if (isinstance(node, _ast.Call) and isinstance(node.func, _ast.Attribute)
                and node.func.attr == "add" and len(node.args) >= 3):
            sev = getattr(node.args[0], "id", "")
            if sev == "INFO":
                continue
            cid = node.args[1].value if isinstance(node.args[1], _ast.Constant) else "(dynamic)"
            msg = node.args[2]
            first = ""
            if isinstance(msg, _ast.Constant):
                first = str(msg.value)
            elif isinstance(msg, _ast.JoinedStr) and msg.values and isinstance(msg.values[0], _ast.Constant):
                first = str(msg.values[0].value)
            if first.startswith("..."):
                continue  # overflow/continuation message, not a distinct condition
            per_class[cid] += 1
    total = sum(per_class.values())
    width = max(len(c) for c in per_class)
    for cid, n in sorted(per_class.items()):
        print(f"  {cid:{width}}  {n}")
    print(f"\n{total} individual checks across {len(per_class)} check classes.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("target", nargs="?", help="stage directory or package .zip")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--emit-manifest", action="store_true",
                    help="write manifest.json (sha256, source commit, tool versions) into the "
                         "stage dir before checking")
    ap.add_argument("--list-checks", action="store_true",
                    help="print every check class with its individual-condition count "
                         "(AST-derived from this file; the source of the advertised numbers)")
    args = ap.parse_args()

    if args.list_checks:
        return list_checks()
    if not args.target:
        ap.error("target is required unless --list-checks is given")

    f = Findings()
    tmp = None
    # resolve to absolute: stage/version tokens are derived from path segments,
    # and a relative target ('.', 'cnd01') yields empty tokens and false blockers
    target = os.path.abspath(args.target)
    if target.endswith(".zip"):
        tmp = tempfile.mkdtemp(prefix="pub_check_")
        try:
            with zipfile.ZipFile(target) as z:
                for name in z.namelist():
                    dest = os.path.realpath(os.path.join(tmp, name))
                    if not dest.startswith(os.path.realpath(tmp) + os.sep):
                        print(f"error: zip entry escapes extraction dir: {name}",
                              file=sys.stderr)
                        return 2
                z.extractall(tmp)
        except zipfile.BadZipFile as e:
            print(f"error: not a readable zip: {e}", file=sys.stderr)
            return 2
        target = locate_stage_dir(tmp)
    if not os.path.isdir(target):
        print(f"error: {target} is not a directory", file=sys.stderr)
        return 2

    if args.emit_manifest:
        version, stage = parse_stage(target)
        print(f"wrote {emit_manifest(target, version, stage)}")

    run(target, f)

    if args.json:
        print(json.dumps({"target": args.target, "findings": f.items,
                          "blockers": f.blockers}, indent=2))
    else:
        # Aggregate repeated same-class warnings so blockers stay readable:
        # 102 case warnings on one KMIP package drowned 3 blockers (Jul 2026).
        # --json always carries the full list.
        by_group: dict[tuple[str, str], list[dict]] = {}
        for item in f.items:
            by_group.setdefault((item["severity"], item["check"]), []).append(item)
        display: list[dict] = []
        for (sev, check), group in by_group.items():
            if sev == WARN and len(group) > 5:
                display.extend(group[:3])
                display.append({"severity": WARN, "check": check,
                                "message": f"...and {len(group) - 3} more '{check}' "
                                           f"warnings (--json lists all)."})
            else:
                display.extend(group)
        order = {BLOCKER: 0, WARN: 1, INFO: 2}
        for item in sorted(display, key=lambda x: order[x["severity"]]):
            print(f"[{item['severity']:7}] {item['check']:13} {item['message']}")
        n_warn = sum(1 for x in f.items if x["severity"] == WARN)
        verdict = "NOT PUBLISHABLE" if f.blockers else "publishable"
        print(f"\n{f.blockers} blocker(s), {n_warn} warning(s) -> {verdict}")

    if tmp:
        shutil.rmtree(tmp, ignore_errors=True)
    return 1 if f.blockers else 0


if __name__ == "__main__":
    sys.exit(main())
