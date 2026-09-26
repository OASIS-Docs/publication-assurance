#!/usr/bin/env python3
# Copyright 2026 OASIS Open
# SPDX-License-Identifier: Apache-2.0
# Authored by Michael Coletta, Technical Advisor to OASIS Open.
"""Cut the next stage of an OASIS Markdown specification.

A Markdown spec has no entities: its stage lives in the title, the stage
line, the date, the This/Previous/Latest stage blocks, the citation, every
cited URL under its own stage path, and the Notices copyright year. This
rewrites exactly those sites and nothing else (no prose, no typos, no
Status wording), asserting how many times it found each one:

    advance_stage.py SRC.md --to csd02 --date 2026-10-01 [--version 1.1]
                     [--previous source|none] [--formats md,html,pdf]
                     [--write] [--out DIR] [--allow-dirty] [--unpublished-ok]

Dry run by default: it prints the diff and a site table and writes nothing.
--write creates <stem>.md for the new stage in --out (default: beside the
source), never over the source or an existing file. It refuses, writing
nothing and exiting 1, when:

  1. the source is not a clean committed file (--allow-dirty overrides);
  2. the target stage is retired, unknown, or misnumbered (os takes no
     number, every other stage needs one);
  3. the target goes backwards within a version, or leaves an os version;
  4. the target changes track (specification to note, or back);
  5. the front matter is not the OASIS Markdown shape (for example a NIEM
     Project Note, whose "Open Project" heading this tool does not know);
  6. any site is found a number of times other than expected, or the
     citation has fields the template does not know;
  7. the version changes and --previous is not given: the first stage of a
     new version has no agreed Previous stage (CSAF writes N/A, DMLex cites
     the prior OS), so the editor chooses;
  8. the target is a Working Draft without --unpublished-ok: wd URIs are
     not published on docs.oasis-open.org and will not resolve.

The stage vocabulary is imported from oasis_pub_check.py, so the tool and
the gate cannot disagree about which stages exist. Run the gate on the
result: it cross-checks every site this tool wrote. Standard library only.
"""

from __future__ import annotations

import argparse
import difflib
import importlib.util
import os
import re
import subprocess
import sys
from datetime import date

_spec = importlib.util.spec_from_file_location(
    "oasis_pub_check", os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "oasis_pub_check.py"))
_gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_gate)
VALID_STAGE_PREFIXES = _gate.VALID_STAGE_PREFIXES
RETIRED_STAGE_TOKENS = _gate.RETIRED_STAGE_TOKENS

STAGE_NAMES = {"wd": "Working Draft", "csd": "Committee Specification Draft",
               "cs": "Committee Specification", "os": "OASIS Standard",
               "cnd": "Committee Note Draft", "cn": "Committee Note"}
TRACK = {"wd": "spec", "csd": "spec", "cs": "spec", "os": "spec", "cnd": "note", "cn": "note"}
ORDER = {"wd": 0, "csd": 1, "cnd": 1, "cs": 2, "cn": 2, "os": 3}
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August",
          "September", "October", "November", "December"]
FRONT_HEADINGS = ["This stage:", "Previous stage:", "Latest stage:", "Technical Committee:"]
STAGE_URL = re.compile(r"https?://docs\.oasis-open\.org/(?P<root>[\w./-]+?)/v(?P<ver>\d+\.\d+)"
                       r"/(?P<stage>[a-z]+\d*)/(?P<stem>[\w.-]+?)\.(?P<ext>md|html|pdf|docx)"
                       r"(?P<auth> \(Authoritative\))?")


class Refused(Exception):
    """A condition the tool will not guess its way through."""


def split_stage(token: str) -> tuple[str, str]:
    m = re.fullmatch(r"([a-z]+)(\d{2})?", token or "")
    if not m:
        raise Refused(f"{token!r} is not a stage token")
    return m.group(1), m.group(2) or ""


def stage_label(token: str) -> str:
    kind, num = split_stage(token)
    return STAGE_NAMES[kind] + (f" {num}" if num else "")


def check_target(old: str, new: str, same_version: bool, unpublished_ok: bool,
                 prev_drafts: tuple[int, ...] = ()) -> None:
    kind, num = split_stage(new)
    if kind in RETIRED_STAGE_TOKENS or new in RETIRED_STAGE_TOKENS:
        raise Refused(f"{new} is a retired stage (Naming Directives v1.7); use csd, cnd, cs, cn or os")
    if kind not in VALID_STAGE_PREFIXES or kind not in STAGE_NAMES:
        raise Refused(f"{kind} is not a stage this tool can cut")
    if kind == "os" and num:
        raise Refused("os takes no revision number")
    if kind != "os" and not num:
        raise Refused(f"{kind} needs a two-digit revision number, e.g. {kind}01")
    if kind == "wd" and not unpublished_ok:
        raise Refused("Working Drafts are not published on docs.oasis-open.org, so their stage "
                      "URIs will not resolve; pass --unpublished-ok to cut one anyway")
    okind, onum = split_stage(old)
    if TRACK[kind] != TRACK.get(okind, TRACK[kind]):
        raise Refused(f"{old} to {new} changes track (specification and note are separate tracks)")
    if not same_version:
        return
    if okind == "os":
        raise Refused(f"{old} is the final stage of this version; cut the next version instead")
    if kind == "os" and okind != "cs":
        raise Refused(f"an OASIS Standard follows a Committee Specification, not {old}")
    if kind == okind and int(num) <= int(onum or 0):
        raise Refused(f"{new} does not come after {old}")
    if ORDER[kind] < ORDER[okind]:
        # A new draft after an approved stage continues the draft numbering.
        # The highest draft the document cites as its Previous stage is the
        # evidence; without one, the draft number must exceed the approved
        # stage's (CSAF v2.0: cs01, then csd03).
        floor = max(prev_drafts) if prev_drafts else int(onum)
        if not (kind in ("csd", "cnd") and okind in ("cs", "cn") and int(num) > floor):
            raise Refused(f"{new} goes backwards from {old}, or reuses a stage that exists "
                          f"(the next draft here is numbered above {floor:02d})")


def check_version(old: str, new: str) -> None:
    if not re.fullmatch(r"\d+\.\d+", new or ""):
        raise Refused(f"version {new!r} is not of the form X.Y")
    if tuple(map(int, new.split("."))) <= tuple(map(int, old.split("."))):
        raise Refused(f"version {new} does not come after {old}")


URL = r"https?://docs\.oasis-open\.org/[^\s<>)\]]+"


class StageAdvance:
    """Parse one OASIS Markdown spec and rewrite its stage-bound sites."""

    def __init__(self, text: str):
        self.crlf = "\r\n" in text
        self.src = text.replace("\r\n", "\n")
        self.sites: list[tuple[str, int, int]] = []    # (site, expected, found)
        self.stale: list[str] = []
        head = self.src.split("\n## Notices", 1)[0]
        headings = re.findall(r"(?m)^#### (.+?)\s*$", head)
        if [h for h in headings if h in FRONT_HEADINGS] != FRONT_HEADINGS or \
                re.search(r"(?m)^#### Open Project:", head) or \
                re.search(r"(?m)^## OASIS Project Note", head):
            raise Refused("front matter is not the OASIS Markdown shape (This/Previous/Latest "
                          "stage, then Technical Committee)")
        block = self._block("This stage:").group("body")
        urls = list(STAGE_URL.finditer(block))
        if not urls:
            raise Refused("no docs.oasis-open.org URL of the form <root>/vX.Y/<stage>/<file> in "
                          "the This stage block (a multi-part spec with files in a subdirectory "
                          "is not supported)")
        first = urls[0]
        self.root, self.version, self.stage = first["root"], first["ver"], first["stage"]
        self.stem = first["stem"]
        self.formats = [u["ext"] for u in urls]
        self.authoritative = next((u["ext"] for u in urls if u["auth"]), None)
        self.bracketed = "<http" in block
        if any((u["root"], u["ver"], u["stage"], u["stem"]) !=
               (self.root, self.version, self.stage, self.stem) for u in urls):
            raise Refused("This stage URLs do not share one stage path and file name")

    # -- parsing helpers ---------------------------------------------------
    def _block(self, heading: str, text: str | None = None):
        m = re.search(rf"(?ms)^(?P<head>#### {re.escape(heading)}[ \t]*\n\n?)(?P<body>.*?)"
                      rf"(?P<tail>\n\n?)(?=#### |---|## )", text if text is not None else self.src)
        if not m:
            raise Refused(f"no '#### {heading}' block")
        return m

    def _sub(self, text: str, old: str, new: str, expected: int, site: str) -> str:
        found = text.count(old)
        self.sites.append((site, expected, found))
        if found != expected:
            raise Refused(f"{site}: expected {expected}, found {found}")
        return text.replace(old, new)

    def _replace_block(self, s: str, heading: str, new_body: str, site: str) -> str:
        m = self._block(heading, s)
        return self._sub(s, m.group(0), m.group("head") + new_body + m.group("tail"), 1, site)

    @staticmethod
    def _stage_urls(root, ver, stage, stem, formats, auth, bracketed=False) -> str:
        base = f"https://docs.oasis-open.org/{root}/v{ver}/" + (f"{stage}/" if stage else "")
        wrap = (lambda u: f"<{u}>") if bracketed else (lambda u: u)
        lines = [wrap(f"{base}{stem}.{ext}") + (" (Authoritative)" if ext == auth else "")
                 for ext in formats]
        return " \\\n".join(lines)

    # -- the rewrite -------------------------------------------------------
    def advance(self, to: str, when: date, version: str | None = None,
                previous: str | None = None, formats: list[str] | None = None,
                unpublished_ok: bool = False, leave_stale: bool = False) -> str:
        new_ver = version or self.version
        same = new_ver == self.version
        if not same:
            check_version(self.version, new_ver)
        prev_block = self._block("Previous stage:").group("body")
        draft_kind = {"cs": "csd", "cn": "cnd"}.get(self.stage.rstrip("0123456789"), "")
        prev_drafts = tuple(int(n) for n in re.findall(
            rf"/v{re.escape(self.version)}/{draft_kind}(\d{{2}})/", prev_block)) if draft_kind else ()
        check_target(self.stage, to, same, unpublished_ok, prev_drafts)
        if not same and previous is None:
            raise Refused("the version changes, so the Previous stage is the editor's choice: "
                          "pass --previous source (cite this document's stage) or --previous none")
        previous = previous or "source"
        if previous not in ("source", "none"):
            raise Refused("--previous takes source or none")
        wp = self.stem.split(f"-v{self.version}")[0]
        new_stem = f"{wp}-v{new_ver}-{to}"
        fmts = formats or self.formats
        auth = self.authoritative if self.authoritative in fmts else None
        s = self.src
        # title
        if not same:
            t = re.search(rf"(?m)^(# .*? Version ){re.escape(self.version)}\b(.*)$", s)
            if not t:
                raise Refused(f"title: no '# ... Version {self.version}' line")
            s = self._sub(s, t.group(0), t.group(1) + new_ver + t.group(2), 1, "title version")
        # stage line and date: the two level-2 headings after the title
        m = re.search(r"(?m)^## (.+)\n\n## (\d{1,2} [A-Z][a-z]+ \d{4})\n", s)
        if not m or m.group(1) != stage_label(self.stage):
            raise Refused(f"stage line: expected '## {stage_label(self.stage)}' then a date")
        pad = "02d" if re.fullmatch(r"0\d .*", m.group(2)) else "d"
        new_date = f"{when.day:{pad}} {MONTHS[when.month - 1]} {when.year}"
        s = self._sub(s, m.group(0), f"## {stage_label(to)}\n\n## {new_date}\n", 1, "stage line and date")
        # This stage
        s = self._replace_block(s, "This stage:", self._stage_urls(
            self.root, new_ver, to, new_stem, fmts, auth, self.bracketed), "This stage block")
        # citation label and body
        s = self._citation(s, new_ver, to, new_date, new_stem, wp)
        # every other URL under the old stage path, before Previous is written
        old_dir = re.compile(rf"(https?)://docs\.oasis-open\.org/{re.escape(self.root)}/"
                             rf"v{re.escape(self.version)}/{re.escape(self.stage)}/([^\s<>)\]]*)")

        def move(mm):
            rest = mm.group(2)
            if rest.startswith(self.stem):
                rest = new_stem + rest[len(self.stem):]
            return f"{mm.group(1)}://docs.oasis-open.org/{self.root}/v{new_ver}/{to}/{rest}"
        s, n = old_dir.subn(move, s)
        self.sites.append(("self URLs under the stage path", n, n))
        # Previous stage: this document's own stage, every format it lists
        prev_new = "N/A" if previous == "none" else self._stage_urls(
            self.root, self.version, self.stage, self.stem, self.formats, self.authoritative,
            self.bracketed)
        s = self._replace_block(s, "Previous stage:", prev_new, "Previous stage block")
        # Latest stage: the version root, in the formats and form it already uses
        latest = self._block("Latest stage:", s).group("body")
        exts = [u.rsplit(".", 1)[-1] for u in re.findall(URL, latest)]
        latest_auth = next((e for e in exts if re.search(
            rf"\.{e}>? \(Authoritative\)", latest)), None)
        s = self._replace_block(s, "Latest stage:", self._stage_urls(
            self.root, new_ver, "", f"{wp}-v{new_ver}", exts or ["html", "pdf"], latest_auth,
            "<http" in latest), "Latest stage block")
        # Notices copyright years (a range keeps its first year)
        years = re.findall(r"(?m)^Copyright © OASIS Open ((?:\d{4}-)?\d{4})\.", s)
        if not years:
            raise Refused("Notices: no 'Copyright © OASIS Open YYYY.' line")
        if len(set(years)) > 1:
            raise Refused(f"Notices: copyright lines disagree ({', '.join(sorted(set(years)))})")
        start = years[0].split("-")[0] + "-" if "-" in years[0] else ""
        s = self._sub(s, f"Copyright © OASIS Open {years[0]}.",
                      f"Copyright © OASIS Open {start}{when.year}.", len(years),
                      "Notices copyright year")
        # Anything that still names the source's stage, outside the Previous
        # stage block, was not a site this tool knows how to rewrite: a URL
        # wrapped across lines, the file name in a code sample, a sibling work
        # product's path. List it; never guess.
        prev_now = self._block("Previous stage:", s).group(0)
        rest = s.replace(prev_now, "\n" * prev_now.count("\n"), 1)
        stale_re = re.compile(rf"/v{re.escape(self.version)}/{re.escape(self.stage)}/|"
                              rf"\.\./{re.escape(self.stage)}/|"
                              rf"(?<![A-Za-z0-9-]){re.escape(self.stem)}(?![A-Za-z0-9])", re.I)
        self.stale = [f"line {i}: {ln.strip()}" for i, ln in enumerate(rest.split("\n"), 1)
                      if stale_re.search(ln)]
        if self.stale and not leave_stale:
            raise Refused("stale stage references this tool does not rewrite (edit them, or "
                          "pass --leave-stale to write the cut and list them):\n  "
                          + "\n  ".join(self.stale))
        self.new_stem = new_stem
        return s.replace("\n", "\r\n") if self.crlf else s

    def _citation(self, s, new_ver, to, new_date, new_stem, wp) -> str:
        block = s.split("#### Citation format:", 1)
        if len(block) != 2:
            raise Refused("no '#### Citation format:' section")
        cite = block[1].split("\n---", 1)[0]
        lab = re.search(r"(?m)^(\\\[|\*\*\[)([^\]\\]*?)" + re.escape(self.version) +
                        r"(\\\]|\]\*\*)[ \t]*$", cite)
        if not lab:
            raise Refused("citation label: expected a [name-X.Y] label carrying the version")
        paras = [p for p in re.split(r"\n[ \t]*\n", cite) if re.match(r"\s*(\*(?!\*)|_)", p)]
        if len(paras) != 1:
            raise Refused(f"citation body: expected one paragraph starting with the title, "
                          f"found {len(paras)}")
        flat = re.sub(r"\s*\n\s*", " ", paras[0].strip())
        body = re.fullmatch(
            r"(?P<d>[*_])(?P<title>[^*_]+?)(?P=d)\. Edited by (?P<eds>.+?)\. "
            r"(?P<date>\d{1,2} [A-Z][a-z]+ \d{4})\. OASIS (?P<stage>.+?)\. "
            r"(?P<lt><?)(?P<this>https://docs\.oasis-open\.org/\S+?)>?\. "
            r"Latest (?P<lw>version|stage): <?(?P<latest>https://docs\.oasis-open\.org/\S+?)>?\.",
            flat)
        if not body:
            raise Refused("citation body: fields the template does not know (expected "
                          "Title. Edited by ... Date. OASIS Stage. <this>. Latest version: <latest>.)")
        close = ">" if body["lt"] else ""
        name = "OASIS Standard" if to == "os" else f"OASIS {stage_label(to)}"
        this_url = f"https://docs.oasis-open.org/{self.root}/v{new_ver}/{to}/{new_stem}.html"
        latest = f"https://docs.oasis-open.org/{self.root}/v{new_ver}/{wp}-v{new_ver}.html"
        title = body["title"].replace(f"Version {self.version}", f"Version {new_ver}")
        new_body = (f"{body['d']}{title}{body['d']}. Edited by {body['eds']}. {new_date}. {name}. "
                    f"{body['lt']}{this_url}{close}. Latest {body['lw']}: "
                    f"{body['lt']}{latest}{close}.")
        new_label = lab.group(1) + lab.group(2) + new_ver + lab.group(3)
        new_cite = cite.replace(lab.group(0), new_label, 1).replace(paras[0].strip(), new_body, 1)
        self.sites.append(("citation label", 1, 1))
        self.sites.append(("citation body", 1, 1))
        return block[0] + "#### Citation format:" + new_cite + block[1][len(cite):]


def source_is_clean(path: str) -> tuple[bool, str]:
    d = os.path.dirname(os.path.abspath(path))
    try:
        sha = subprocess.run(["git", "-C", d, "log", "-1", "--format=%h", "--", path],
                             capture_output=True, text=True, check=True).stdout.strip()
        dirty = subprocess.run(["git", "-C", d, "status", "--porcelain", "--", path],
                               capture_output=True, text=True, check=True).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False, "not in a git repository"
    if not sha:
        return False, "not committed"
    return (not dirty), (f"commit {sha}" if not dirty else f"modified since commit {sha}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("source")
    ap.add_argument("--to", required=True, help="target stage token: csd02, cs01, os, ...")
    ap.add_argument("--date", required=True, type=date.fromisoformat, help="YYYY-MM-DD")
    ap.add_argument("--version", help="new version X.Y when cutting a new version")
    ap.add_argument("--previous", choices=["source", "none"],
                    help="Previous stage: this document's stage, or N/A")
    ap.add_argument("--formats", help="This stage formats, e.g. md,html,pdf (default: the source's)")
    ap.add_argument("--write", action="store_true", help="create the new file (default: dry run)")
    ap.add_argument("--out", help="directory for the new file (default: beside the source)")
    ap.add_argument("--allow-dirty", action="store_true")
    ap.add_argument("--unpublished-ok", action="store_true")
    ap.add_argument("--leave-stale", action="store_true",
                    help="write the cut even when references to the old stage remain, and list them")
    a = ap.parse_args(argv)
    try:
        clean, where = source_is_clean(a.source)
        print(f"source: {a.source} ({where})")
        if not clean and not a.allow_dirty:
            raise Refused(f"source is {where}; commit it first so the cut is reproducible, "
                          "or pass --allow-dirty")
        text = open(a.source, encoding="utf-8").read()
        adv = StageAdvance(text)
        out = adv.advance(a.to, a.date, a.version, a.previous,
                          a.formats.split(",") if a.formats else None, a.unpublished_ok,
                          a.leave_stale)
    except Refused as e:
        print(f"REFUSED: {e}", file=sys.stderr)
        return 1
    print(f"{'site':34} expected found")
    for site, exp, got in adv.sites:
        print(f"{site:34} {exp:>8} {got:>5}")
    target = os.path.join(a.out or os.path.dirname(os.path.abspath(a.source)), adv.new_stem + ".md")
    sys.stdout.writelines(difflib.unified_diff(text.splitlines(True), out.splitlines(True),
                                               a.source, target, n=0))
    for line in adv.stale:
        print(f"STALE {line}")
    print("Not inspected: prose outside these sites, the Status wording, conformance text, "
          "and any typo. Run oasis_pub_check.py on the staged result.")
    if not a.write:
        print("dry run: nothing written (pass --write)")
        return 0
    if os.path.exists(target):
        print(f"REFUSED: {target} exists", file=sys.stderr)
        return 1
    with open(target, "w", encoding="utf-8") as fh:
        fh.write(out)
    print(f"wrote {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
