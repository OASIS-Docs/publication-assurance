"""Publishing a run's report files to the reports branch, and linking them.

pub-check/publish_report.py commits the files to an orphan branch and states
their full URLs in the step summary, a ::notice and the action outputs. These
tests run it against a local bare repository standing in for GitHub (the
remote is <GITHUB_SERVER_URL>/<GITHUB_REPOSITORY>.git, so a file:// server
URL is a real git remote) and read back what landed on the branch.
"""

from __future__ import annotations

import http.server
import json
import os
import subprocess
import sys
import threading
from pathlib import Path

import pytest

from conftest import CORPUS, REPO_ROOT, run_cli, stage_from_corpus

PUBLISH = REPO_ROOT / "pub-check" / "publish_report.py"
REPORT = REPO_ROOT / "pub-check" / "validation_report.py"


def git(cwd, *args) -> str:
    return subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True,
                          check=True).stdout


@pytest.fixture(scope="module")
def files(tmp_path_factory) -> Path:
    """The files the gate step leaves in RUNNER_TEMP, from the CSAF corpus."""
    tmp = tmp_path_factory.mktemp("run")
    stage = stage_from_corpus(tmp / "pkg", CORPUS / "csaf" / "v2.1" / "csd01")
    gate = run_cli("--json", str(stage))
    out = tmp / "files"
    out.mkdir()
    (out / "oasis-pub-check.json").write_text(gate.stdout)
    (out / "oasis-pub-check.txt").write_text("findings\n")
    subprocess.run([sys.executable, str(REPORT), str(out / "oasis-pub-check.json"),
                    "--md", str(out / "pubcheck-validation.md"),
                    "--html", str(out / "pubcheck-validation.html")], check=True,
                   capture_output=True)
    (out / "pubcheck-validation.pdf").write_bytes(b"%PDF-1.4 stand-in\n")
    return out


@pytest.fixture
def remote(tmp_path) -> Path:
    """A bare repository <tmp>/server/OASIS/tc.git with a main branch."""
    bare = tmp_path / "server" / "OASIS" / "tc.git"
    bare.parent.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", "--bare", str(bare)], check=True)
    seed = tmp_path / "seed"
    subprocess.run(["git", "init", "-q", "-b", "main", str(seed)], check=True)
    (seed / "README.md").write_text("code\n")
    git(seed, "add", "-A")
    git(seed, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "code")
    git(seed, "push", "-q", str(bare), "main")
    return bare


def publish(tmp_path, files, remote, *, branch="pubcheck-reports", title="CSAF v2.1 CSD01",
            extra_env=None) -> tuple[subprocess.CompletedProcess, dict, str]:
    out = tmp_path / f"github-output-{title}"
    out.write_text("")
    links = tmp_path / f"links-{title}.md"
    env = {**os.environ, "GITHUB_SERVER_URL": f"file://{remote.parent.parent}",
           "GITHUB_API_URL": "http://127.0.0.1:9", "GITHUB_REPOSITORY": "OASIS/tc",
           "GITHUB_REF_NAME": "main", "GITHUB_RUN_ID": "42", "GITHUB_OUTPUT": str(out),
           "PUBLISH_TOKEN": "t0ken", **(extra_env or {})}
    env.pop("GITHUB_HEAD_REF", None)
    env.pop("GITHUB_EVENT_PATH", None)
    env.update(extra_env or {})
    r = subprocess.run([sys.executable, str(PUBLISH), "--files", str(files), "--branch", branch,
                        f"--title={title}", "--links-md", str(links)],
                       capture_output=True, text=True, env=env, timeout=120)
    outputs = dict(line.split("=", 1) for line in out.read_text().splitlines())
    return r, outputs, links.read_text() if links.exists() else ""


def test_first_publish_creates_an_orphan_branch_with_every_file_and_the_links(
        tmp_path, files, remote):
    r, out, links = publish(tmp_path, files, remote)
    assert r.returncode == 0, r.stderr
    assert out["report_publish_note"] == "published", out
    folder = "main/csaf-v2.1-csd01"
    listing = git(remote, "ls-tree", "-r", "--name-only", "pubcheck-reports").split()
    for name in ("pubcheck-validation.pdf", "pubcheck-validation.md", "pubcheck-validation.html",
                 "pubcheck-report.json", "pubcheck-report.txt", "meta.json"):
        assert f"{folder}/{name}" in listing, listing
    assert "index.html" in listing and ".nojekyll" in listing
    # An orphan: no history shared with the code branch.
    merge_base = subprocess.run(["git", "-C", str(remote), "merge-base", "main",
                                 "pubcheck-reports"], capture_output=True)
    assert merge_base.returncode != 0

    server = f"file://{remote.parent.parent}/OASIS/tc"
    sha = git(remote, "rev-parse", "pubcheck-reports").strip()
    assert out["report_url_pdf"] == f"{server}/blob/pubcheck-reports/{folder}/pubcheck-validation.pdf"
    assert out["report_url_md"] == f"{server}/blob/pubcheck-reports/{folder}/pubcheck-validation.md"
    assert out["report_url_folder"] == f"{server}/tree/pubcheck-reports/{folder}"
    assert out["report_url_pdf_pinned"] == f"{server}/blob/{sha}/{folder}/pubcheck-validation.pdf"
    # Without Pages the HTML link is the source view, labelled as such, with the fix.
    assert out["report_url_html"].endswith(f"/blob/pubcheck-reports/{folder}/pubcheck-validation.html")
    assert links.startswith("### Validation report: CSAF v2.1 CSD01")
    assert f"[PDF (opens in GitHub)]({out['report_url_pdf']})" in links
    assert "HTML (source view)" in links and "Deploy from a branch > pubcheck-reports / (root)" in links
    assert f"::notice title=Validation report::PDF (opens in GitHub): {out['report_url_pdf']}" \
        in r.stdout
    index = git(remote, "show", "pubcheck-reports:index.html")
    assert f'href="{folder}/pubcheck-validation.html"' in index


def test_a_second_run_replaces_its_folder_and_keeps_the_others(tmp_path, files, remote):
    publish(tmp_path, files, remote, title="first")
    publish(tmp_path, files, remote, title="second")
    r, out, _ = publish(tmp_path, files, remote, title="first")
    assert out["report_publish_note"] == "published", r.stderr
    listing = git(remote, "ls-tree", "-r", "--name-only", "pubcheck-reports").split()
    assert "main/first/meta.json" in listing and "main/second/meta.json" in listing
    assert int(git(remote, "rev-list", "--count", "pubcheck-reports")) == 3
    index = git(remote, "show", "pubcheck-reports:index.html")
    assert index.index("main/first/") < index.index("main/second/"), "newest run first"


def test_concurrent_matrix_calls_all_land(tmp_path, files, remote):
    """Red-team counterexample: matrix jobs push to one branch at once. A
    push that loses the race must fetch, re-apply on the new tip and push
    again, so no job's report is dropped."""
    env = {**os.environ, "GITHUB_SERVER_URL": f"file://{remote.parent.parent}",
           "GITHUB_API_URL": "http://127.0.0.1:9", "GITHUB_REPOSITORY": "OASIS/tc",
           "GITHUB_REF_NAME": "main", "PUBLISH_TOKEN": "t"}
    procs = [subprocess.Popen([sys.executable, str(PUBLISH), "--files", str(files),
                               f"--title=job-{i}", "--links-md", str(tmp_path / f"l{i}")],
                              env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
             for i in range(6)]
    for p in procs:
        p.wait(timeout=120)
    listing = git(remote, "ls-tree", "-r", "--name-only", "pubcheck-reports").split()
    missing = [i for i in range(6) if f"main/job-{i}/meta.json" not in listing]
    assert not missing, f"reports lost to the race: {missing}"


def test_publishing_off_leaves_the_repository_alone_and_says_why(tmp_path, files, remote):
    r, out, links = publish(tmp_path, files, remote, branch="")
    assert r.returncode == 0
    assert out["report_publish_note"] == "publishing is off (`publish-branch` is empty)"
    assert out["report_url_pdf"] == "" and out["report_url_folder"] == ""
    assert "Report not published: publishing is off" in links
    assert "actions/runs/42" in links
    assert git(remote, "branch", "--list").split() == ["main"]


def test_a_token_without_write_access_does_not_fail_and_says_why(tmp_path, files, remote):
    hook = remote / "hooks" / "pre-receive"
    hook.write_text("#!/bin/sh\necho 'Permission to OASIS/tc.git denied to github-actions[bot].'"
                    " >&2\nexit 1\n")
    hook.chmod(0o755)
    r, out, links = publish(tmp_path, files, remote)
    assert r.returncode == 0
    assert "permissions: contents: write" in out["report_publish_note"], out
    assert out["report_url_pdf"] == ""
    assert "Report not published" in links


def test_a_fork_pull_request_is_not_published(tmp_path, files, remote):
    event = tmp_path / "event.json"
    event.write_text(json.dumps({"pull_request": {"head": {"repo": {"full_name": "someone/tc"}}}}))
    r, out, _ = publish(tmp_path, files, remote, extra_env={"GITHUB_EVENT_PATH": str(event)})
    assert "pull request from a fork" in out["report_publish_note"]
    assert git(remote, "branch", "--list").split() == ["main"]


def test_the_token_is_on_no_command_line_and_in_no_file(tmp_path, files, remote):
    r, _, _ = publish(tmp_path, files, remote)
    assert "t0ken" not in r.stdout + r.stderr
    assert b"t0ken" not in b"".join(p.read_bytes() for p in remote.rglob("*") if p.is_file())


def test_pages_serving_the_branch_puts_the_rendered_html_first(tmp_path, files, remote):
    class Pages(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            body = json.dumps({"html_url": "https://oasis.github.io/tc/",
                               "source": {"branch": "pubcheck-reports", "path": "/"}}).encode()
            self.send_response(200)
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *a):
            pass

    srv = http.server.HTTPServer(("127.0.0.1", 0), Pages)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        r, out, links = publish(tmp_path, files, remote, extra_env={
            "GITHUB_API_URL": f"http://127.0.0.1:{srv.server_port}"})
    finally:
        srv.shutdown()
    page = "https://oasis.github.io/tc/main/csaf-v2.1-csd01/pubcheck-validation.html"
    assert out["report_url_html"] == page, out
    assert links.split("\n- ")[1].startswith(f"[HTML report (opens in browser)]({page})")
    assert f"::notice title=Validation report::HTML report (opens in browser): {page}" in r.stdout
    assert "source view" not in links
