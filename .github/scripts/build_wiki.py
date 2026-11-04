#!/usr/bin/env python3
# Copyright 2026 OASIS Open
# SPDX-License-Identifier: Apache-2.0
# Authored by Michael Coletta, Technical Advisor to OASIS Open.
"""Build the GitHub Wiki pages from the repository's markdown.

The markdown in the repository is the single source. This script copies each
guide to a wiki page and rewrites its links for the wiki:

- a link to another guide becomes a link to that guide's wiki page, keeping
  any #anchor;
- a link to any other file in the repository goes to its github.com blob URL
  (a directory to its tree URL);
- an image goes to its raw.githubusercontent.com URL, because a relative image
  path in a wiki resolves against the wiki repository and breaks.

Links inside fenced blocks and inline code are left as written. Each page
ends with a note naming the file it was generated from. Home, _Sidebar and
_Footer come from docs/wiki/ and are rewritten the same way.

The script refuses to write anything if a relative link names a file that
does not exist, so a broken link fails the build instead of reaching the wiki.

Usage: build_wiki.py --out <dir> [--repo OWNER/NAME] [--ref main]
"""
from __future__ import annotations

import argparse
import posixpath
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# Source path (relative to the repository root) -> wiki page name.
# The one place the mapping lives; the sidebar, the tests and the rewriter
# all read it.
PAGES: dict[str, str] = {
    "docs/wiki/Home.md": "Home",
    "docs/wiki/_Sidebar.md": "_Sidebar",
    "docs/wiki/_Footer.md": "_Footer",
    "README.md": "Repository-overview",
    "docs/ADOPTING.md": "Adoption-guide",
    "PUBLICATION-QUALITY.md": "Publication-quality",
    "docs/WORKED-EXAMPLES.md": "Worked-examples",
    "docs/CONVERT-AND-VERIFY.md": "Convert-and-verify",
    "docs/MARKDOWN-EDITION.md": "Markdown-edition",
    "TRANSFORMS.md": "Markdown-pipeline",
    "pub-check/README.md": "The-checker",
    "pub-check/CHECKS.md": "Check-catalog",
    "pub-check/AUTHORITIES.md": "Policy-authorities",
    "pub-check/rules/README.md": "Source-text-rules",
    "pub-check/corpus/README.md": "Policy-corpus",
    "render/README.md": "Rendering",
    "verify/README.md": "Verifying-a-conversion",
    "converters/docbook-to-markdown/README.md": "DocBook-to-Markdown-converter",
    "harvest/README.md": "Learning-from-check-records",
    "assets/architecture/README.md": "Architecture-diagrams",
    "examples/eox-core-v1.0-csd01/README.md": "Example-validation-report",
    "CHANGELOG.md": "Changelog",
}

# Pages that carry no "generated from" note: the footer already says it for
# every page, and the sidebar is a menu.
NO_SOURCE_NOTE = {"_Sidebar", "_Footer"}

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"}

FENCE = re.compile(r"(?ms)^([ \t]*)(`{3,}|~{3,})(?!`)[^`\n]*\n.*?^[ \t]*\2[ \t]*$")
INLINE_CODE = re.compile(r"`[^`\n]*`")
MD_LINK = re.compile(r"(!?)\[((?:[^\[\]]|\[[^\]]*\])*)\]\(([^)\s]+)((?:\s+\"[^\"]*\")?)\)")
HTML_ATTR = re.compile(r"""(\b(?:href|src)=)(["'])([^"']+)\2""")
SCHEME = re.compile(r"^[a-z][a-z0-9+.-]*:", re.I)


class BrokenLink(Exception):
    pass


class WikiBuilder:
    def __init__(self, root: Path, repo: str, ref: str):
        self.root = root
        self.repo = repo
        self.ref = ref
        self.broken: list[str] = []

    # -- link resolution -------------------------------------------------
    def resolve(self, source: str, target: str, image: bool) -> str:
        if not target or target.startswith("#") or SCHEME.match(target):
            return target
        path, sep, frag = target.partition("#")
        path, qsep, query = path.partition("?")
        repo_path = posixpath.normpath(posixpath.join(posixpath.dirname(source), path))
        if repo_path.startswith("../") or repo_path == "..":
            self.broken.append(f"{source}: {target} (outside the repository)")
            return target
        disk = self.root / repo_path
        if not disk.exists():
            self.broken.append(f"{source}: {target}")
            return target
        anchor = f"#{frag}" if sep else ""
        query = f"?{query}" if qsep else ""
        if repo_path in PAGES and not image:
            return PAGES[repo_path] + anchor
        if image or disk.suffix.lower() in IMAGE_SUFFIXES and not disk.is_dir():
            return f"https://raw.githubusercontent.com/{self.repo}/{self.ref}/{repo_path}{query}"
        kind = "tree" if disk.is_dir() else "blob"
        suffix = "" if repo_path == "." else f"/{repo_path}"
        if repo_path == ".":
            return f"https://github.com/{self.repo}{anchor}"
        return f"https://github.com/{self.repo}/{kind}/{self.ref}{suffix}{query}{anchor}"

    def _rewrite_prose(self, source: str, text: str) -> str:
        # Protect inline code, then rewrite markdown links and HTML attributes.
        codes: list[str] = []

        def stash(m):
            codes.append(m.group(0))
            return f"\x00{len(codes) - 1}\x00"

        text = INLINE_CODE.sub(stash, text)
        text = MD_LINK.sub(
            lambda m: f"{m.group(1)}[{m.group(2)}]"
                      f"({self.resolve(source, m.group(3), bool(m.group(1)))}{m.group(4)})",
            text)
        text = HTML_ATTR.sub(
            lambda m: m.group(1) + m.group(2)
            + self.resolve(source, m.group(3), m.group(1).startswith("src"))
            + m.group(2),
            text)
        return re.sub("\x00(\\d+)\x00", lambda m: codes[int(m.group(1))], text)

    def rewrite(self, source: str, text: str) -> str:
        out, pos = [], 0
        for m in FENCE.finditer(text):
            out.append(self._rewrite_prose(source, text[pos:m.start()]))
            out.append(m.group(0))
            pos = m.end()
        out.append(self._rewrite_prose(source, text[pos:]))
        return "".join(out)

    # -- pages -------------------------------------------------------------
    def page(self, source: str) -> str:
        text = (self.root / source).read_text(encoding="utf-8")
        body = self.rewrite(source, text)
        name = PAGES[source]
        if name not in NO_SOURCE_NOTE:
            url = f"https://github.com/{self.repo}/blob/{self.ref}/{source}"
            body = (body.rstrip("\n")
                    + f"\n\n---\n\n*Generated from [{source}]({url}). "
                      "Edit that file, not this page.*\n")
        return body

    def build(self, out: Path) -> list[str]:
        pages = {PAGES[s] + ".md": self.page(s) for s in PAGES}
        if self.broken:
            raise BrokenLink("\n".join(self.broken))
        out.mkdir(parents=True, exist_ok=True)
        for name, body in pages.items():
            (out / name).write_text(body, encoding="utf-8")
        return sorted(pages)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", required=True, type=Path, help="directory to write the pages to")
    ap.add_argument("--repo", default="OASIS-Docs/publication-assurance")
    ap.add_argument("--ref", default="main", help="branch or commit the file links point at")
    args = ap.parse_args(argv)
    try:
        written = WikiBuilder(REPO_ROOT, args.repo, args.ref).build(args.out)
    except BrokenLink as e:
        print(f"broken links, nothing written:\n{e}", file=sys.stderr)
        return 1
    print(f"wrote {len(written)} wiki pages to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
