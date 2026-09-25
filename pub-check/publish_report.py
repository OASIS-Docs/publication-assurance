#!/usr/bin/env python3
# Copyright 2026 OASIS Open
# SPDX-License-Identifier: Apache-2.0
# Authored by Michael Coletta, Technical Advisor to OASIS Open.
"""Publish one run's report files to a reports branch and link them.

The composite action writes the Validation Report on the runner, where a
reader cannot open it. This script commits the run's files to an orphan
branch of the calling repository (default `pubcheck-reports`) under
`<ref>/<slug>/`, rebuilds the branch's `index.html`, and states full
https://github.com links: the PDF and Markdown in GitHub's browser view, the
folder, a PDF link pinned to the report commit, and the HTML report as a
rendered page when GitHub Pages serves the branch.

Publishing never fails the gate. When it cannot happen (publishing turned
off, a pull request from a fork, a token without contents: write) the
reason is stated and the run page is linked instead.

Usage (inside the action; every value arrives in the environment):
  publish_report.py --files <dir> --branch <name> --title <label>
                    [--links-md <out.md>]

<dir> holds oasis-pub-check.json, oasis-pub-check.txt and the
pubcheck-validation.{md,html,pdf} the action rendered. The token is read
from $PUBLISH_TOKEN and never put on a command line. Outputs go to
$GITHUB_OUTPUT, the ::notice annotation to stdout, and the summary block to
--links-md for the summary step to place first.

Standard library only. Exit 0 whether or not anything was published.
"""
from __future__ import annotations

import argparse
import base64
import datetime
import html
import json
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import validation_report  # noqa: E402

FILES = {  # name on the runner -> name on the branch
    "pubcheck-validation.pdf": "pubcheck-validation.pdf",
    "pubcheck-validation.md": "pubcheck-validation.md",
    "pubcheck-validation.html": "pubcheck-validation.html",
    "oasis-pub-check.json": "pubcheck-report.json",
    "oasis-pub-check.txt": "pubcheck-report.txt",
}
ATTEMPTS = 10           # a matrix pushes to one branch; each retry re-applies on the new tip
BOT = ("github-actions[bot]", "41898282+github-actions[bot]@users.noreply.github.com")
PAGES_HOWTO = "Settings > Pages > Deploy from a branch > {branch} / (root)"
MARKER = ".pubcheck-reports"   # at the root of every branch this script created
RESERVED = {"index.html", MARKER, ".nojekyll"}


class NotPublished(Exception):
    """A reason, in words a workflow user can act on, that nothing was pushed."""


def slug(text: str) -> str:
    """A path segment: lowercase letters, digits, dot, dash and underscore."""
    s = re.sub(r"[^a-z0-9._-]+", "-", text.lower()).strip("-.")
    return s[:80].strip("-.") or "report"


def folder_for(env: dict, title: str, target: str) -> str:
    """<ref>/<slug>: the pull request's head branch, else the ref name, then
    the summary title, else the target."""
    ref = slug(env.get("GITHUB_HEAD_REF") or env.get("GITHUB_REF_NAME") or "local")
    # A ref named like a file at the branch root would collide with it.
    return f"{'ref-' + ref if ref in RESERVED else ref}/{slug(title or target)}"


def fork_pull_request(env: dict) -> bool:
    """Whether this run is a pull request from another repository, whose
    token can never write to this one."""
    try:
        with open(env["GITHUB_EVENT_PATH"]) as f:
            event = json.load(f)
    except (KeyError, OSError, ValueError):
        return False
    head = (event.get("pull_request") or {}).get("head", {}).get("repo") or {}
    return bool(head.get("full_name")) and head["full_name"] != env.get("GITHUB_REPOSITORY")


class Branch:
    """A working copy of one branch, fetched and pushed with the token in an
    HTTP header set through the environment, so it is on no command line
    and in no file."""

    def __init__(self, workdir: str, remote: str, branch: str, token: str):
        self.dir, self.branch = workdir, branch
        auth = base64.b64encode(f"x-access-token:{token}".encode()).decode()
        self.env = {**os.environ, "GIT_TERMINAL_PROMPT": "0",
                    "GIT_CONFIG_COUNT": "1",
                    "GIT_CONFIG_KEY_0": f"http.{remote}.extraheader",
                    "GIT_CONFIG_VALUE_0": f"AUTHORIZATION: basic {auth}"}
        self.git("init", "-q")
        self.git("remote", "add", "origin", remote)

    def git(self, *args: str, check: bool = True) -> subprocess.CompletedProcess:
        r = subprocess.run(["git", "-C", self.dir, *args], capture_output=True, text=True,
                           env=self.env)
        if check and r.returncode:
            raise subprocess.CalledProcessError(r.returncode, args[0], r.stdout, r.stderr)
        return r

    def checkout(self) -> bool:
        """The branch tip, or a fresh orphan when the branch does not exist
        yet. Returns whether it existed."""
        r = self.git("ls-remote", "--heads", "origin", f"refs/heads/{self.branch}", check=False)
        if r.returncode:
            raise NotPublished(denied(r.stderr) or "the repository could not be read")
        if not r.stdout.strip():
            self.git("checkout", "-q", "--orphan", self.branch)
            return False
        self.git("fetch", "-q", "--depth=1", "origin",
                 f"+refs/heads/{self.branch}:refs/remotes/origin/{self.branch}")
        self.git("checkout", "-q", "-B", self.branch, f"origin/{self.branch}")
        if not os.path.isfile(os.path.join(self.dir, MARKER)):
            # Somebody's real branch (main, gh-pages): never write into it.
            raise NotPublished(f"branch `{self.branch}` exists and was not created for pub-check "
                               f"reports (it has no {MARKER} file); set `publish-branch` to "
                               "a branch of its own")
        return True

    def commit_and_push(self, message: str) -> str | None:
        """The new commit's SHA, or None when the push lost a race."""
        self.git("add", "-A")
        self.git("-c", f"user.name={BOT[0]}", "-c", f"user.email={BOT[1]}",
                 "commit", "-q", "--allow-empty", "-m", message)
        r = self.git("push", "-q", "origin", f"HEAD:refs/heads/{self.branch}", check=False)
        if r.returncode == 0:
            return self.git("rev-parse", "HEAD").stdout.strip()
        if re.search(r"non-fast-forward|fetch first|rejected|cannot lock ref", r.stderr) \
                and not denied(r.stderr):
            return None
        raise NotPublished(denied(r.stderr) or f"git push failed: {r.stderr.strip()}")


def denied(stderr: str) -> str | None:
    if re.search(r"403|Permission to .* denied|write access .* not granted|"
                 r"Authentication failed|could not read Username", stderr):
        return ("the workflow token cannot write to this repository; give the job "
                "`permissions: contents: write`")
    if re.search(r"protected branch|GH006|GH013|rule violations", stderr):
        return "a branch protection rule or ruleset refuses pushes to the reports branch"
    return None


def write_run(root: str, folder: str, files: str, meta: dict) -> None:
    """Replace this run's folder, rebuild the index, keep Pages from
    running Jekyll over the branch."""
    dest = os.path.join(root, folder)
    shutil.rmtree(dest, ignore_errors=True)
    os.makedirs(dest)
    for src, name in FILES.items():
        if os.path.isfile(os.path.join(files, src)):
            shutil.copyfile(os.path.join(files, src), os.path.join(dest, name))
    with open(os.path.join(dest, "meta.json"), "w") as f:
        json.dump(meta, f, indent=2, sort_keys=True)
    for name in (".nojekyll", MARKER):
        open(os.path.join(root, name), "w").close()
    with open(os.path.join(root, "index.html"), "w") as f:
        f.write(render_index(root))


def render_index(root: str) -> str:
    """Every published folder, newest first, with its verdict: the Pages
    landing page."""
    runs = []
    for ref in sorted(os.listdir(root)):
        for name in (sorted(os.listdir(os.path.join(root, ref)))
                     if os.path.isdir(os.path.join(root, ref)) and not ref.startswith(".") else []):
            try:
                with open(os.path.join(root, ref, name, "meta.json")) as f:
                    runs.append((f"{ref}/{name}", json.load(f)))
            except (OSError, ValueError):
                continue
    runs.sort(key=lambda r: r[1].get("published_at", ""), reverse=True)
    e = html.escape
    rows = []
    for path, m in runs:
        ok = m.get("publication_ready")
        links = [f'<a href="{e(path)}/pubcheck-validation.html">HTML</a>']
        if m.get("pdf"):
            links.append(f'<a href="{e(path)}/pubcheck-validation.pdf">PDF</a>')
        links.append(f'<a href="{e(path)}/">files</a>')
        rows.append(f'<tr><td class="n">{e(m.get("published", ""))}</td>'
                    f'<td class="t">{e(m.get("title", path))}<br><code>{e(path)}</code></td>'
                    f'<td class="r {"PASS" if ok else "BLOCKER"}">'
                    f'{"READY" if ok else "NOT READY"}</td>'
                    f'<td class="t">{e(m.get("verdict", ""))}</td>'
                    f'<td class="n">{" | ".join(links)}</td></tr>')
    return "\n".join([
        "<!DOCTYPE html>", '<html lang="en"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>pub-check reports</title><style>{validation_report.CSS}</style></head>",
        "<body><main><h1>pub-check Validation Reports</h1>",
        f'<p class="note">Every report published to this branch, newest first: '
        f'{len(runs)} report folder(s). Each run replaces its own folder; the branch history '
        "keeps every earlier run.</p>",
        '<div class="wrap"><table><thead><tr><th>Published (UTC)</th><th>Report</th>'
        "<th>Result</th><th>Verdict</th><th>Open</th></tr></thead><tbody>",
        *rows, "</tbody></table></div></main></body></html>", ""])


def pages_site(api: str, repo: str, token: str, branch: str) -> tuple[str | None, str]:
    """(html_url, why) for the GitHub Pages site when it serves `branch`
    from its root, else (None, the reason). Reads the Pages API with the
    token, then without it (a public repository answers either way)."""
    url = f"{api}/repos/{repo}/pages"
    for headers in ({"Authorization": f"Bearer {token}"} if token else None, {}):
        if headers is None:
            continue
        req = urllib.request.Request(url, headers={**headers,
                                                   "Accept": "application/vnd.github+json"})
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                site = json.load(r)
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return None, "GitHub Pages is not enabled for this repository"
            continue    # 401/403: try unauthenticated, then give up
        except (urllib.error.URLError, OSError, ValueError):
            break
        src = site.get("source") or {}
        if src.get("branch") == branch and src.get("path", "/") == "/" and site.get("html_url"):
            return site["html_url"].rstrip("/") + "/", ""
        return None, (f"GitHub Pages serves {src.get('branch')}:{src.get('path')}, "
                      f"not {branch} / (root)")
    return None, "the Pages settings could not be read with this token"


def links_block(title: str, verdict: str, urls: dict, note: str, pages_why: str,
                branch: str, run_url: str) -> str:
    """The summary block: labelled links first, the verdict under them."""
    lines = [f"### Validation report: {title}", "", f"**{verdict}**", ""]
    if not urls:
        return "\n".join(lines + [f"Report not published: {note}. The report files for this "
                                  f"run are on the [run page]({run_url}) under Artifacts "
                                  "when the workflow uploads `report-dir`.", "", ""])
    if urls.get("html_page"):
        lines.append(f"- [HTML report (opens in browser)]({urls['html_page']})")
    lines += [f"- [PDF (opens in GitHub)]({urls['pdf']})" if urls.get("pdf") else
              "- PDF: not produced on this runner (no headless Chrome)",
              f"- [Markdown]({urls['md']})"]
    if not urls.get("html_page"):
        lines.append(f"- [HTML (source view)]({urls['html_blob']}). {pages_why}; to open it as a "
                     f"page: {PAGES_HOWTO.format(branch=branch)}.")
    lines += [f"- [All files for this run]({urls['folder']})"]
    if urls.get("pdf_pinned"):
        lines.append(f"- [This run's PDF, pinned to commit {urls['sha'][:7]}]({urls['pdf_pinned']})")
    return "\n".join(lines + ["", ""])


def command_data(text: str) -> str:
    """Text safe as a workflow command's message: one line, with GitHub's
    escapes for %, CR and LF."""
    return text.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--files", required=True)
    ap.add_argument("--branch", default="pubcheck-reports")
    ap.add_argument("--title", default="")
    ap.add_argument("--links-md", default=None)
    args = ap.parse_args()
    env = os.environ
    server = env.get("GITHUB_SERVER_URL", "https://github.com").rstrip("/")
    api = env.get("GITHUB_API_URL", "https://api.github.com").rstrip("/")
    repo = env.get("GITHUB_REPOSITORY", "")
    run_url = f"{server}/{repo}/actions/runs/{env.get('GITHUB_RUN_ID', '')}"
    token = env.get("PUBLISH_TOKEN", "")

    try:
        with open(os.path.join(args.files, "oasis-pub-check.json")) as f:
            data = json.load(f)
        rec = validation_report.build_record(data, args.title, None, "")
        verdict = f"{validation_report.verdict(rec)} {validation_report.result_line(rec)}"
    except (OSError, ValueError, KeyError, TypeError):
        data, rec, verdict = {}, None, "The gate produced no readable --json report."
    title = " ".join((args.title or data.get("target", "package")).split())
    folder = folder_for(env, args.title, data.get("target", "package"))
    urls: dict = {}
    pages_why = ""
    try:
        if not args.branch:
            raise NotPublished("publishing is off (`publish-branch` is empty)")
        if rec is None:
            raise NotPublished("the gate did not produce a report to publish")
        if not repo:
            raise NotPublished("not running in GitHub Actions (no GITHUB_REPOSITORY)")
        if fork_pull_request(env):
            raise NotPublished("this is a pull request from a fork, whose token cannot write "
                               "to this repository")
        if not token:
            raise NotPublished("no token (`publish-token` is empty)")
        now = datetime.datetime.now(datetime.timezone.utc)
        meta = {"title": title, "target": data.get("target", ""), "folder": folder,
                "ref": env.get("GITHUB_HEAD_REF") or env.get("GITHUB_REF_NAME", ""),
                "source_sha": env.get("GITHUB_SHA", ""), "run_url": run_url,
                "published": now.strftime("%Y-%m-%d %H:%M:%S"),
                "published_at": now.isoformat(),
                "publication_ready": rec["publication_ready"], "verdict": verdict,
                "pdf": os.path.isfile(os.path.join(args.files, "pubcheck-validation.pdf"))}
        remote = f"{server}/{repo}.git"
        sha = None
        for attempt in range(ATTEMPTS):
            with tempfile.TemporaryDirectory(prefix="pubcheck-publish-") as work:
                branch = Branch(work, remote, args.branch, token)
                branch.checkout()
                write_run(work, folder, args.files, meta)
                sha = branch.commit_and_push(
                    f"pub-check report: {folder} (run {env.get('GITHUB_RUN_ID', '')})")
            if sha:
                break
            # Someone else pushed first. Random backoff, so a matrix that
            # collided once does not collide again in lockstep.
            time.sleep(random.uniform(0.5, 2.0 + attempt))
        if not sha:
            raise NotPublished(f"the reports branch kept moving; {ATTEMPTS} pushes lost the race")
        q = urllib.parse.quote
        base = f"{server}/{repo}/blob/{q(args.branch, safe='/')}/{folder}"
        urls = {"md": f"{base}/pubcheck-validation.md",
                "html_blob": f"{base}/pubcheck-validation.html",
                "folder": f"{server}/{repo}/tree/{q(args.branch, safe='/')}/{folder}",
                "sha": sha}
        if meta["pdf"]:
            urls["pdf"] = f"{base}/pubcheck-validation.pdf"
            urls["pdf_pinned"] = f"{server}/{repo}/blob/{sha}/{folder}/pubcheck-validation.pdf"
        site, pages_why = pages_site(api, repo, token, args.branch)
        if site:
            urls["html_page"] = f"{site}{folder}/pubcheck-validation.html"
        note = "published"
    except NotPublished as exc:
        note = " ".join(str(exc).split())
    except (subprocess.CalledProcessError, OSError) as exc:
        detail = getattr(exc, "stderr", "") or str(exc)
        note = f"publishing failed: {' '.join(detail.split())}"
        urls = {}

    outputs = {"report_url_pdf": urls.get("pdf", ""), "report_url_md": urls.get("md", ""),
               "report_url_html": urls.get("html_page") or urls.get("html_blob", ""),
               "report_url_folder": urls.get("folder", ""),
               "report_url_pdf_pinned": urls.get("pdf_pinned", ""),
               "report_publish_note": note}
    out = env.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a") as f:
            f.writelines(f"{k}={v}\n" for k, v in outputs.items())
    if urls.get("html_page"):
        notice = f"HTML report (opens in browser): {urls['html_page']}"
    elif urls.get("pdf"):
        notice = f"PDF (opens in GitHub): {urls['pdf']}"
    elif urls:
        notice = f"Markdown report: {urls['md']}"
    else:
        notice = f"Report not published: {note}. Files for this run: {run_url}"
    print(f"::notice title=Validation report::{command_data(notice)}")
    block = links_block(title, verdict, urls, note, pages_why, args.branch, run_url)
    if args.links_md:
        with open(args.links_md, "w") as f:
            f.write(block)
    else:
        print(block)
    return 0


if __name__ == "__main__":
    sys.exit(main())
