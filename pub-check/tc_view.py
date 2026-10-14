#!/usr/bin/env python3
# Copyright 2026 OASIS Open
# SPDX-License-Identifier: Apache-2.0
# Authored by Michael Coletta, Technical Advisor to OASIS Open.
"""The result of the checks as a committee member sees it: outcome first, then what to fix.

Reads one `oasis_pub_check.py --json` report and turns each finding into a row
an editor can act on: where it is (file and line, linked to the file at the
commit when the file is in the repository), what is wrong in plain English,
and how to fix it. The plain text comes from plain_language.py; the finding's
own message travels beside it as the exact detail. Nothing here changes a
finding, a count or an exit code.

Where a finding is: the checker's messages do not carry a location field, so
it is read from the message, deterministically, in this order:
  1. "markdown line N" / "HTML line N" (or "Line N:" opening the message, or
     "Markdown lines N, M, ..." where the first is used) in the message: that
     line of the package's Markdown or HTML delivery file.
  2. A message that opens with a package file's path and a colon: that file,
     at the first line holding a phrase or address the message quotes.
  3. A quoted phrase (8 characters or more) or a web address in the message
     that occurs verbatim in the package's Markdown, then HTML: its first line.
  4. A check about the PDF: the package's PDF, with no line.
A finding that matches none of these is shown without a location. A zip
target is never located: its files are not in the repository.

Subcommands:
  tc_view.py annotate <report.json> --package-dir DIR
      Print GitHub workflow commands (::error / ::warning with file and line)
      for each located blocker and warning, at most GitHub's 10 of each per
      step, then one ::notice for the rest.
  tc_view.py comment <report.json> --package-dir DIR [--title T] [--run-url U]
      Create or update one pull request comment with the outcome, the tables
      and what was resolved since the previous run. Needs GITHUB_TOKEN (or
      $PR_COMMENT_TOKEN) with pull-requests: write; without it, a ::warning
      and exit 0.
  tc_view.py markdown <report.json> --package-dir DIR
      Print the outcome and the tables as GitHub Markdown (a local look).

Standard library only. Exit 0 on success, 2 when the input is not a --json report.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import html
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from plain_language import explain  # noqa: E402
from validation_report import md_cell, md_text  # noqa: E402

SEV_ORDER = {"BLOCKER": 0, "WARN": 1, "INFO": 2}
ANNOTATION_LIMIT = 10     # GitHub shows at most 10 error and 10 warning annotations per step
TABLE_LIMIT = 30          # rows per table in the step summary and the pull request comment
COMMENT_LIMIT = 60_000    # GitHub refuses a comment body over 65,536 characters
MARKER = "<!-- oasis-publication-checks: {slot} -->"
STATE = re.compile(r"<!-- oasis-publication-checks-state: ([A-Za-z0-9+/=]*) -->")
PDF_CLASSES = {"pdf-cover", "pdf-fonts", "pdf-legibility", "pdf-sync", "pdf-toc-pages", "generator"}
LINE_IN_MESSAGE = re.compile(r"\b(markdown|html)\s+lines?\s+\(?(\d+)", re.I)   # a list: its first line
JSON_POSITION = re.compile(r"\bline (\d+) column \d+")
LINE_AT_START = re.compile(r"^Line (\d+): ")   # the Markdown checks' own form (md-links, fence-collapse)
DIGITS = re.compile(r"\d+")
STATE_LIMIT = 20_000      # characters of encoded state carried in the comment
QUOTED = re.compile(r"'([^'\n]{8,})'")
URL = re.compile(r"https?://[^\s'\"<>()\[\]]+")


def plural(n: int, word: str) -> str:
    return f"{n} {word}" if n == 1 else f"{n} {word}s"


def counts(findings: list[dict]) -> tuple[int, int, int]:
    sev = [f.get("severity") for f in findings]
    return sev.count("BLOCKER"), sev.count("WARN"), sev.count("INFO")


def headline(findings: list[dict]) -> str:
    """The one-line outcome: 'Publishable' or 'Not publishable: N blockers, M warnings'."""
    b, w, _ = counts(findings)
    if b:
        return f"Not publishable: {plural(b, 'blocker')}, {plural(w, 'warning')}"
    return f"Publishable ({plural(w, 'warning')} to review)" if w else "Publishable"


def finding_key(f: dict) -> str:
    """A stable identity for one finding across runs: its class and message
    with every number blanked. A line number or a count moves when unrelated
    text is edited, and a finding that only moved is not resolved. Two
    findings that differ only in a number share a key, so one fixed while the
    other stays is not listed as resolved: the list errs towards silence."""
    msg = DIGITS.sub("#", f.get("message", ""))
    raw = f"{f.get('check', '')}\0{msg}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


# ---------------------------------------------------------------- locations

class Package:
    """The package's own files, read once, for locating findings."""

    def __init__(self, pkg_dir: str | None):
        self.dir = pkg_dir if pkg_dir and os.path.isdir(pkg_dir) else None
        self.files: list[str] = []
        self._text: dict[str, list[str]] = {}
        self._main: dict[str, str] | None = None
        if not self.dir:
            return
        for root, dirs, names in os.walk(self.dir):
            dirs[:] = sorted(d for d in dirs if not d.startswith("."))
            for n in sorted(names):
                self.files.append(os.path.relpath(os.path.join(root, n), self.dir).replace(os.sep, "/"))

    def main(self, ext: str) -> str | None:
        """The package's delivery item in one format (md, html, pdf), chosen
        by the checker's own rule, so a finding lands on the file that was
        checked and never on a -DIFF PDF or a comment resolution log."""
        if self._main is None:
            from oasis_pub_check import find_delivery_items
            try:
                found = find_delivery_items(self.dir)
            except OSError:
                found = {}
            self._main = {k: os.path.basename(v) for k, v in found.items()}
        return self._main.get(ext)

    def lines(self, rel: str) -> list[str]:
        """The file's lines as git and GitHub count them: split at LF only, so
        a form feed or U+2028 in the text does not shift the numbering."""
        if rel not in self._text:
            try:
                with open(os.path.join(self.dir, rel), encoding="utf-8", errors="replace",
                          newline="") as fh:
                    self._text[rel] = fh.read().split("\n")
            except OSError:
                self._text[rel] = []
        return self._text[rel]

    def find(self, snippet: str, rel: str) -> int | None:
        for i, line in enumerate(self.lines(rel), 1):
            if snippet in line:
                return i
        return None

    def locate(self, f: dict) -> tuple[str, int | None] | None:
        if not self.dir:
            return None
        msg = f.get("message", "")
        md = self.main("md")
        page = self.main("html")
        m = LINE_IN_MESSAGE.search(msg)
        start = LINE_AT_START.match(msg)
        if m or start:
            rel = page if m and m.group(1).lower() == "html" else md
            n = int(m.group(2) if m else start.group(1))
            if rel and 0 < n <= len(self.lines(rel)):
                return rel, n
        snippets = sorted(set(QUOTED.findall(msg)) | {u.rstrip(".,;:") for u in URL.findall(msg)},
                          key=len, reverse=True)
        head = msg.split(": ", 1)[0]
        if head in self.files:
            # The message names the file; a JSON parser's "line N column M",
            # or a quoted value from the file, gives the line.
            j = JSON_POSITION.search(msg)
            if j and 0 < int(j.group(1)) <= len(self.lines(head)):
                return head, int(j.group(1))
            for s in snippets:
                n = self.find(s, head)
                if n:
                    return head, n
            return head, None
        for rel in (md, page):
            if not rel:
                continue
            for s in snippets:
                # A web address is placed where it is a link target first: the
                # same address usually also appears, earlier, as cover text.
                n = (self.find(f"]({s})", rel) or self.find(f'href="{s}"', rel)
                     if URL.fullmatch(s) else None) or self.find(s, rel)
                if n:
                    return rel, n
        if f.get("check") in PDF_CLASSES:
            pdf = self.main("pdf")
            if pdf:
                return pdf, None
        return None


class Repo:
    """Turns a package file into its path in the calling repository and, when
    the file is committed there, a link to it at the commit under test."""

    def __init__(self, pkg_dir: str | None, env: dict | None = None):
        env = os.environ if env is None else env
        self.base = None
        if pkg_dir and os.path.isdir(pkg_dir):
            ws = env.get("GITHUB_WORKSPACE") or os.getcwd()
            path = pkg_dir if os.path.isabs(pkg_dir) else os.path.join(os.getcwd(), pkg_dir)
            rel = os.path.relpath(os.path.realpath(path), os.path.realpath(ws))
            if not rel.startswith(".."):
                self.base = rel.replace(os.sep, "/")
        server = env.get("GITHUB_SERVER_URL", "").rstrip("/")
        repo = env.get("GITHUB_REPOSITORY", "")
        self.sha = head_sha(env)
        self.blob = f"{server}/{repo}/blob/{self.sha}/" if server and repo and self.sha else ""
        self._tracked: set[str] | None = None

    def path(self, rel: str) -> str:
        if self.base is None:
            return rel
        return os.path.normpath(os.path.join(self.base, rel)).replace(os.sep, "/")

    def tracked(self, path: str) -> bool:
        if self._tracked is None:
            try:
                out = subprocess.run(["git", "ls-files", "-z", "--", self.base or "."],
                                     capture_output=True, text=True, timeout=30)
                self._tracked = set(out.stdout.split("\0")) if out.returncode == 0 else set()
            except (OSError, subprocess.SubprocessError):
                self._tracked = set()
        return path in self._tracked

    def url(self, path: str, line: int | None) -> str:
        if not self.blob or self.base is None or not self.tracked(path):
            return ""
        plain = "?plain=1" if path.lower().endswith(".md") else ""
        return self.blob + urllib.parse.quote(path) + plain + (f"#L{line}" if line else "")


def head_sha(env) -> str:
    """The commit a reader means: a pull request's head, else the pushed commit."""
    event = env.get("GITHUB_EVENT_PATH", "")
    if event and os.path.isfile(event):
        try:
            with open(event) as fh:
                pr = json.load(fh).get("pull_request") or {}
            sha = (pr.get("head") or {}).get("sha")
            if sha:
                return sha
        except (OSError, ValueError, AttributeError):
            pass
    return env.get("GITHUB_SHA", "")


def rows(findings: list[dict], pkg_dir: str | None, env: dict | None = None) -> list[dict]:
    """One row per finding, blockers first, each class's findings together."""
    pkg, repo = Package(pkg_dir), Repo(pkg_dir, env)
    out = []
    for f in sorted(findings, key=lambda f: (SEV_ORDER.get(f.get("severity"), 9), f.get("check", ""))):
        what, fix = explain(f.get("check", ""), f.get("message", ""), f.get("severity", ""))
        where = pkg.locate(f)
        row = {"severity": f.get("severity", ""), "check": f.get("check", ""), "what": what,
               "fix": fix, "detail": f.get("message", ""), "key": finding_key(f),
               "file": None, "line": None, "url": ""}
        if where:
            row["file"] = repo.path(where[0])
            row["line"] = where[1]
            row["url"] = repo.url(row["file"], where[1])
        out.append(row)
    return out


# ---------------------------------------------------------------- Markdown

NO_PLACE = "Not tied to one line"


def where_md(r: dict) -> str:
    if not r["file"]:
        return NO_PLACE
    label = md_cell(r["file"] + (f" line {r['line']}" if r["line"] else ""))
    return f"[{label}]({r['url']})" if r["url"] else label


def table_md(rs: list[dict], limit: int | None) -> list[str]:
    lines = ["| Where | What is wrong | How to fix it |", "|---|---|---|"]
    shown = rs if limit is None else rs[:limit]
    prev = None
    for r in shown:
        found = f"<br><sub>Found: {md_cell(r['detail'])}</sub>"
        if (r["what"], r["fix"]) == prev:
            lines.append(f"| {where_md(r)} | Same as above.{found} | As above. |")
        else:
            lines.append(f"| {where_md(r)} | {md_cell(r['what'])}{found} | {md_cell(r['fix'])} |")
        prev = (r["what"], r["fix"])
    if limit is not None and len(rs) > limit:
        lines += ["", f"...and {len(rs) - limit} more, listed in the full report."]
    return lines


def outcome_md(findings: list[dict], rs: list[dict], limit: int | None = TABLE_LIMIT,
               level: str = "###") -> str:
    """The outcome line, the blockers table, and the warnings table collapsed."""
    b, w, i = counts(findings)
    lines = [f"**{md_text(headline(findings))}**", ""]
    if b:
        lines += ["The document cannot be published until each blocker below is fixed.", ""]
    elif w:
        lines += ["Nothing stops publication. The warnings below are worth a look before you submit.", ""]
    else:
        lines += ["Nothing to fix.", ""]
    blockers = [r for r in rs if r["severity"] == "BLOCKER"]
    warns = [r for r in rs if r["severity"] == "WARN"]
    if blockers:
        lines += [f"{level} Blockers: fix these", ""] + table_md(blockers, limit) + [""]
    if warns:
        lines += ["<details>", f"<summary>{plural(w, 'warning')}: worth checking, but they do not "
                  "stop publication</summary>", ""] + table_md(warns, limit) + ["", "</details>", ""]
    if i:
        lines += [f"{plural(i, 'note')} for information only, with nothing to change, "
                  "are in the full report.", ""]
    return "\n".join(lines)


# ---------------------------------------------------------------- HTML

def outcome_html(findings: list[dict], rs: list[dict]) -> str:
    """The same outcome for the HTML report: no row limit."""
    e = html.escape
    b, w, i = counts(findings)
    out = [f'<section class="outcome"><p class="verdict {"no" if b else "ok"}">{e(headline(findings))}</p>']
    out.append("<p>" + ("The document cannot be published until each blocker below is fixed."
                        if b else "Nothing stops publication." + (" The warnings below are worth a look."
                                                                   if w else "")) + "</p>")

    def table(title: str, sel: list[dict]) -> None:
        out.append(f"<h2>{e(title)}</h2>")
        out.append('<div class="wrap"><table><thead><tr><th>Where</th><th>What is wrong</th>'
                   "<th>How to fix it</th></tr></thead><tbody>")
        prev = None
        for r in sel:
            where = NO_PLACE
            if r["file"]:
                label = e(r["file"] + (f" line {r['line']}" if r["line"] else ""))
                where = f'<a href="{e(r["url"])}">{label}</a>' if r["url"] else f"<code>{label}</code>"
            same = (r["what"], r["fix"]) == prev
            what = "Same as above." if same else e(r["what"])
            fix = "As above." if same else e(r["fix"])
            out.append(f'<tr><td class="t">{where}</td><td class="t f">{what}<br><small>Found: '
                       f'{e(r["detail"])}</small></td><td class="t">{fix}</td></tr>')
            prev = (r["what"], r["fix"])
        out.append("</tbody></table></div>")

    blockers = [r for r in rs if r["severity"] == "BLOCKER"]
    warns = [r for r in rs if r["severity"] == "WARN"]
    if blockers:
        table("Blockers: fix these", blockers)
    if warns:
        table(f"{plural(w, 'warning')}: worth checking, but they do not stop publication", warns)
    if i:
        out.append(f'<p class="note">{plural(i, "note")} for information only, with nothing to '
                   "change, are in the tables below.</p>")
    out.append("</section>")
    return "\n".join(out)


# ---------------------------------------------------------------- annotations

def command_value(text: str) -> str:
    return text.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def command_property(text: str) -> str:
    return command_value(text).replace(":", "%3A").replace(",", "%2C")


def annotations(rs: list[dict], limit: int = ANNOTATION_LIMIT) -> list[str]:
    """Workflow commands for the located blockers (errors) and warnings."""
    out, left = [], {"BLOCKER": 0, "WARN": 0}
    shown = {"BLOCKER": 0, "WARN": 0}
    for r in rs:
        sev = r["severity"]
        if sev not in shown or not r["file"]:
            continue
        if shown[sev] >= limit:
            left[sev] += 1
            continue
        shown[sev] += 1
        props = f"file={command_property(r['file'])}"
        if r["line"]:
            props += f",line={r['line']}"
        props += f",title={command_property(r['what'])}"
        kind = "error" if sev == "BLOCKER" else "warning"
        out.append(f"::{kind} {props}::{command_value(r['fix'] + ' Found: ' + r['detail'])}")
    if left["BLOCKER"] or left["WARN"]:
        out.append("::notice title=More findings than GitHub shows here::"
                   f"{plural(left['BLOCKER'], 'more blocker')} and {plural(left['WARN'], 'more warning')} "
                   "are not marked on the files. They are all listed in the job summary and the report.")
    return out


# ---------------------------------------------------------------- pull request comment

def slot_for(title: str) -> str:
    """The comment's marker for one title: readable, and unique to the exact
    title (two titles that read alike, or share a long prefix, get two comments)."""
    readable = re.sub(r"[^A-Za-z0-9._/-]+", "-", title).strip("-")[:80] or "package"
    return f"{readable}-{hashlib.sha256(title.encode('utf-8')).hexdigest()[:8]}"


def encode_state(rs: list[dict]) -> str:
    """This run's blockers and warnings, for the next run's 'resolved' list,
    within STATE_LIMIT: with their text when it fits, else identities only,
    else as many identities as fit (the list then errs towards silence)."""
    items = [{"k": r["key"], "s": r["severity"], "c": r["check"], "d": r["detail"]}
             for r in rs if r["severity"] in ("BLOCKER", "WARN")]

    def enc(xs: list[dict]) -> str:
        return base64.b64encode(json.dumps(xs, separators=(",", ":")).encode("utf-8")).decode("ascii")

    out = enc(items)
    if len(out) > STATE_LIMIT:
        items = [dict(x, d="") for x in items]
        out = enc(items)
    while len(out) > STATE_LIMIT and items:
        items = items[: len(items) * 3 // 4]
        out = enc(items)
    return out


def decode_state(body: str) -> list[dict]:
    """The previous run's state. The comment can be edited by anyone who can
    edit it, so every field is checked and anything malformed is dropped."""
    m = STATE.search(body or "")
    if not m:
        return []
    try:
        items = json.loads(base64.b64decode(m.group(1), validate=True).decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return []
    if not isinstance(items, list):
        return []
    return [x for x in items[:2000] if isinstance(x, dict)
            and all(isinstance(x.get(k), str) for k in ("k", "s", "c", "d"))]


def resolved(previous: list[dict], rs: list[dict]) -> list[dict]:
    now = {r["key"] for r in rs}
    return [p for p in previous if p["k"] not in now]


def comment_body(findings: list[dict], rs: list[dict], title: str, previous: list[dict] | None,
                 run_url: str = "", sha: str = "") -> str:
    slot = slot_for(title)
    lines = [MARKER.format(slot=slot), f"### OASIS publication checks: {md_text(title)}", "",
             outcome_md(findings, rs, level="####")]
    gone = resolved(previous or [], rs)
    if gone:
        lines += [f"#### Resolved since the last run ({len(gone)})", ""]
        for p in gone[:TABLE_LIMIT]:
            what = explain(p.get("c", ""), p.get("d", ""), p.get("s", ""))[0]
            detail = f" Found was: {md_cell(p['d'])}" if p.get("d") else ""
            lines.append(f"- {md_cell(what)}{detail}")
        if len(gone) > TABLE_LIMIT:
            lines.append(f"- ...and {len(gone) - TABLE_LIMIT} more.")
        lines.append("")
    foot = "This comment is updated on every run."
    if sha:
        foot = f"Checked commit {sha[:7]}. " + foot
    if run_url:
        foot += f" [Full report and run details]({run_url})."
    lines += [f"<sub>{foot}</sub>", "", f"<!-- oasis-publication-checks-state: {encode_state(rs)} -->"]
    body = "\n".join(lines)
    for limit in (5, 0):
        if len(body) <= COMMENT_LIMIT:
            break
        lines[3] = outcome_md(findings, rs, limit=limit, level="####")
        body = "\n".join(lines)
    return body


def pr_number(env) -> int | None:
    if env.get("GITHUB_EVENT_NAME") not in ("pull_request", "pull_request_target"):
        return None
    try:
        with open(env.get("GITHUB_EVENT_PATH", "")) as fh:
            n = (json.load(fh).get("pull_request") or {}).get("number")
        return int(n) if n else None
    except (OSError, ValueError, TypeError, AttributeError):
        return None


class Api:
    def __init__(self, env):
        self.base = env.get("GITHUB_API_URL", "https://api.github.com").rstrip("/")
        self.repo = env.get("GITHUB_REPOSITORY", "")
        self.token = env.get("PR_COMMENT_TOKEN") or env.get("GITHUB_TOKEN", "")

    def call(self, method: str, path: str, body: dict | None = None):
        req = urllib.request.Request(
            f"{self.base}{path}", method=method,
            data=json.dumps(body).encode("utf-8") if body is not None else None,
            headers={"Authorization": f"Bearer {self.token}",
                     "Accept": "application/vnd.github+json",
                     "X-GitHub-Api-Version": "2022-11-28",
                     "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8") or "null")


BOT = "github-actions[bot]"   # the author of every comment the default workflow token writes


def own_logins(api: Api) -> set[str]:
    """Who this token writes as: the Actions bot, and for a personal token
    its user (GET /user refuses the workflow token, which is fine)."""
    logins = {BOT}
    try:
        me = api.call("GET", "/user")
        if isinstance(me, dict) and isinstance(me.get("login"), str):
            logins.add(me["login"])
    except (urllib.error.URLError, OSError, ValueError):
        pass
    return logins


def find_comment(api: Api, number: int, marker: str) -> dict | None:
    """Our comment for this marker: written by this token's identity, never
    a comment someone else wrote with the marker pasted in."""
    mine = own_logins(api)
    for page in range(1, 31):
        batch = api.call("GET", f"/repos/{api.repo}/issues/{number}/comments?per_page=100&page={page}")
        if not batch:
            return None
        for c in batch:
            if (c.get("body") or "").startswith(marker) and \
                    ((c.get("user") or {}).get("login") in mine):
                return c
        if len(batch) < 100:
            return None
    return None


NO_PERMISSION = ("the workflow token cannot write to pull requests. Add 'pull-requests: write' "
                 "under 'permissions:' in the job (a pull request from a fork never gets it); "
                 "the checks themselves are unaffected")


def post_comment(findings: list[dict], rs: list[dict], title: str, env=None,
                 api: Api | None = None) -> str:
    """Create or update the one comment for this title. Returns what happened."""
    env = os.environ if env is None else env
    number = pr_number(env)
    if number is None:
        return "skipped: this run is not for a pull request"
    api = api or Api(env)
    if not api.token or not api.repo:
        return "skipped: no token or repository in the environment"
    marker = MARKER.format(slot=slot_for(title))
    server = env.get("GITHUB_SERVER_URL", "https://github.com").rstrip("/")
    run_url = f"{server}/{api.repo}/actions/runs/{env['GITHUB_RUN_ID']}" if env.get("GITHUB_RUN_ID") else ""
    try:
        existing = find_comment(api, number, marker)
        body = comment_body(findings, rs, title, decode_state(existing["body"]) if existing else None,
                            run_url, head_sha(env))
        if existing:
            try:
                api.call("PATCH", f"/repos/{api.repo}/issues/comments/{existing['id']}", {"body": body})
                return f"updated comment {existing['id']}"
            except urllib.error.HTTPError as exc:
                if exc.code not in (403, 404):
                    raise
                # Someone else's comment carrying our marker: post our own.
        made = api.call("POST", f"/repos/{api.repo}/issues/{number}/comments", {"body": body})
        return f"created comment {(made or {}).get('id')}"
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403, 404):
            return f"warning: could not comment on the pull request: {NO_PERMISSION} (HTTP {exc.code})"
        return f"warning: could not comment on the pull request: HTTP {exc.code}"
    except (urllib.error.URLError, OSError, ValueError) as exc:
        return f"warning: could not comment on the pull request: {exc}"


# ---------------------------------------------------------------- command line

def load(path: str) -> dict:
    with open(path) as fh:
        data = json.load(fh)
    if not isinstance(data, dict) or not isinstance(data.get("findings"), list):
        raise ValueError("no 'findings' list")
    return data


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("command", choices=("annotate", "comment", "markdown"))
    ap.add_argument("report_json")
    ap.add_argument("--package-dir", default=None,
                    help="the checked stage directory (the action's target); omit for a zip")
    ap.add_argument("--title", default="", help="label; defaults to the report's target")
    args = ap.parse_args(argv)
    try:
        data = load(args.report_json)
    except (OSError, ValueError) as exc:
        print(f"tc_view: {args.report_json} is not a --json report: {exc}", file=sys.stderr)
        return 2
    findings = data["findings"]
    rs = rows(findings, args.package_dir)
    title = args.title or str(data.get("target", "package"))
    if args.command == "annotate":
        for line in annotations(rs):
            print(line)
    elif args.command == "markdown":
        print(outcome_md(findings, rs))
    else:
        result = post_comment(findings, rs, title)
        if result.startswith("warning: "):
            print(f"::warning title=Pull request comment not posted::{command_value(result[9:])}")
        else:
            print(f"pull request comment: {result}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
