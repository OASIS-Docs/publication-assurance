# Copyright 2026 OASIS Open
# SPDX-License-Identifier: Apache-2.0
# Authored by Michael Coletta, Technical Advisor to OASIS Open.
"""The committee's view of a run: outcome line, what to fix, where, and the PR comment.

pub-check/tc_view.py and pub-check/plain_language.py turn a --json report into
the outcome line, tables of blockers and warnings in plain English, GitHub
annotations, and one pull request comment updated in place. None of it may
change a finding, a count or an exit code.
"""
from __future__ import annotations

import base64
import importlib.util
import io
import json
import os
import re
import subprocess
import sys
import urllib.error
from pathlib import Path

import yaml

from conftest import CORPUS, REPO_ROOT, run_cli, stage_from_corpus

PUB = REPO_ROOT / "pub-check"
sys.path.insert(0, str(PUB))
EM_DASH = chr(0x2014)


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, PUB / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


plain_language = load("plain_language")
tc_view = load("tc_view")

CSAF_CSD01 = CORPUS / "csaf" / "v2.1" / "csd01"


def check_classes() -> set[str]:
    result = run_cli("--list-checks")
    assert result.returncode == 0, result.stderr
    found = set(re.findall(r"(?m)^  ([a-z0-9-]+)\s+\d+$", result.stdout))
    total = re.search(r"across (\d+) check classes", result.stdout)
    assert total and len(found) == int(total.group(1)), result.stdout
    return found


# ---------------------------------------------------------------- the text table

def test_every_check_class_has_plain_text_and_no_other_entries():
    classes = check_classes()
    assert len(classes) > 50, classes
    missing = classes - set(plain_language.PLAIN)
    extra = set(plain_language.PLAIN) - classes
    assert not missing, f"check classes with no plain-language entry: {sorted(missing)}"
    assert not extra, f"plain-language entries for classes the checker lacks: {sorted(extra)}"


def test_plain_text_is_plain():
    """Each entry says what is wrong and what to change, in sentences, without
    the checker's own vocabulary or an em dash."""
    jargon = re.compile(r"pub-check|oasis_pub_check|pandoc|nide|Kavi|This-stage|\bAST\b|"
                        r"\bBLOCKER\b|\bWARN\b|registry|stage token|" + EM_DASH)
    for check, (what, fix) in plain_language.PLAIN.items():
        for text in (what, fix):
            assert text.strip() and text.rstrip().endswith((".", ")")), (check, text)
            assert not jargon.search(text), (check, text)


# ---------------------------------------------------------------- the outcome line

def f(sev: str, check: str = "residue", message: str = "m") -> dict:
    return {"severity": sev, "check": check, "message": message}


def test_outcome_line_counts_blockers_and_warnings():
    assert tc_view.headline([]) == "Publishable"
    assert tc_view.headline([f("INFO")]) == "Publishable"
    assert tc_view.headline([f("WARN"), f("WARN", message="n")]) == "Publishable (2 warnings to review)"
    assert tc_view.headline([f("BLOCKER"), f("WARN"), f("INFO")]) == \
        "Not publishable: 1 blocker, 1 warning"
    assert tc_view.headline([f("BLOCKER"), f("BLOCKER", message="x")]) == \
        "Not publishable: 2 blockers, 0 warnings"


# ---------------------------------------------------------------- locations

def package(tmp_path: Path) -> Path:
    stage = tmp_path / "spec" / "v1.0" / "csd01"
    stage.mkdir(parents=True)
    md = ["# Title", "", "This version:", "<https://docs.oasis-open.org/x/v1.0/csd01/x.md>",
          "", "TODO: fill this in", "", "See [https://example.org/a](https://example.org/a)."]
    (stage / "x-v1.0-csd01.md").write_text("\n".join(md) + "\n")
    (stage / "x-v1.0-csd01.html").write_text("<h1>Title</h1>\n<p>Only in 'the html' here</p>\n")
    (stage / "x-v1.0-csd01.pdf").write_bytes(b"%PDF-1.4\n")
    (stage / "schema").mkdir()
    (stage / "schema" / "a.json").write_text("{}")
    return stage


def test_a_finding_is_located_from_its_own_words(tmp_path):
    stage = package(tmp_path)
    pkg = tc_view.Package(str(stage))
    md, page = "x-v1.0-csd01.md", "x-v1.0-csd01.html"
    assert pkg.locate(f("INFO", message="heading 'Annex A' (markdown line 6) has no label")) == (md, 6)
    assert pkg.locate(f("WARN", message="Code block at Markdown line 3 differs")) == (md, 3)
    assert pkg.locate(f("BLOCKER", "schema-id", "schema/a.json: $id is wrong")) == ("schema/a.json", None)
    assert pkg.locate(f("BLOCKER", message="URL points at 'x-v1.0-csd01/x.md>' oops")) is None
    assert pkg.locate(f("BLOCKER", message="URL points at 'csd01/x.md>' which is missing")) == (md, 4)
    assert pkg.locate(f("WARN", "md-links", "Dual link: https://example.org/a")) == (md, 8)
    assert pkg.locate(f("WARN", message="quoted 'the html' here")) == (page, 2)
    assert pkg.locate(f("BLOCKER", "pdf-cover", "title appears 2 times")) == ("x-v1.0-csd01.pdf", None)
    assert pkg.locate(f("BLOCKER", "residue", "nothing quoted at all")) is None


def test_a_short_quote_does_not_place_a_finding():
    """'csd01' occurs all over a document: a quote under eight characters
    would put the finding on whichever line happens to come first."""
    assert tc_view.QUOTED.findall("stage 'csd01' and 'v1.0' named") == []


def test_a_line_number_past_the_end_of_the_file_is_not_used(tmp_path):
    """A line that does not exist would put the annotation nowhere; the
    finding is then shown without a location rather than at a wrong one."""
    pkg = tc_view.Package(str(package(tmp_path)))
    assert pkg.locate(f("INFO", message="(markdown line 9999)")) is None


def test_a_zip_or_missing_target_is_never_located(tmp_path):
    zip_path = tmp_path / "x.zip"
    zip_path.write_bytes(b"PK")
    for target in (str(zip_path), str(tmp_path / "absent"), None):
        assert tc_view.Package(target).locate(f("INFO", message="(markdown line 1)")) is None


def test_rows_link_a_committed_file_at_the_commit_under_test(tmp_path, monkeypatch):
    package(tmp_path)
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "add", "spec/v1.0/csd01/x-v1.0-csd01.md"], check=True)
    event = tmp_path / "event.json"
    event.write_text(json.dumps({"pull_request": {"number": 7, "head": {"sha": "abc123"}}}))
    env = {"GITHUB_WORKSPACE": str(tmp_path), "GITHUB_SERVER_URL": "https://github.com",
           "GITHUB_REPOSITORY": "o/r", "GITHUB_SHA": "merge0", "GITHUB_EVENT_PATH": str(event)}
    monkeypatch.chdir(tmp_path)
    rs = tc_view.rows([f("WARN", "md-links", "Dual link: https://example.org/a"),
                       f("BLOCKER", "pdf-cover", "title twice")], "spec/v1.0/csd01", env)
    blocker, warning = rs
    assert blocker["severity"] == "BLOCKER", "blockers come first"
    assert blocker["file"] == "spec/v1.0/csd01/x-v1.0-csd01.pdf"
    assert blocker["url"] == "", "the PDF is not committed, so it gets no link"
    assert warning["file"] == "spec/v1.0/csd01/x-v1.0-csd01.md" and warning["line"] == 8
    assert warning["url"] == ("https://github.com/o/r/blob/abc123/spec/v1.0/csd01/"
                              "x-v1.0-csd01.md?plain=1#L8"), "the head commit, not the merge commit"


# ---------------------------------------------------------------- annotations

def row(sev: str, file: str | None = "a.md", line: int | None = 1, detail: str = "d") -> dict:
    return {"severity": sev, "check": "residue", "what": "What, it: is", "fix": "Fix it.",
            "detail": detail, "key": "k", "file": file, "line": line, "url": ""}


def test_annotations_are_capped_at_githubs_limit_and_the_rest_counted():
    rs = [row("BLOCKER") for _ in range(13)] + [row("WARN") for _ in range(11)] + \
         [row("BLOCKER", file=None), row("INFO")]
    out = tc_view.annotations(rs)
    assert sum(1 for x in out if x.startswith("::error ")) == 10
    assert sum(1 for x in out if x.startswith("::warning ")) == 10
    assert out[-1].startswith("::notice ") and "3 more blockers and 1 more warning" in out[-1], out[-1]


def test_an_annotation_cannot_be_broken_by_the_text_it_carries():
    """A comma or colon in a property ends it early, and a newline in the
    message ends the command: GitHub's escapes, not the raw characters."""
    out = tc_view.annotations([row("BLOCKER", file="dir,x/a:b.md", line=4, detail="two\nlines 100%")])
    assert out == ["::error file=dir%2Cx/a%3Ab.md,line=4,title=What%2C it%3A is::"
                   "Fix it. Found: two%0Alines 100%25"], out


# ---------------------------------------------------------------- Markdown

def test_the_tables_put_blockers_first_and_collapse_warnings():
    findings = [f("WARN", "md-links", "w1"), f("BLOCKER", "residue", "b1"),
                f("BLOCKER", "residue", "b2 | <details> `x`"), f("INFO", "content-labels", "i")]
    text = tc_view.outcome_md(findings, tc_view.rows(findings, None))
    assert text.startswith("**Not publishable: 2 blockers, 1 warning**")
    blockers, warnings = text.split("<details>")
    assert "b1" in blockers and "b2" in blockers and "w1" not in blockers
    assert "w1" in warnings and "1 note for information only" in warnings
    assert "Same as above." in blockers, "the second residue row repeats no text"
    # The finding's own text cannot end the cell or open markup.
    assert "b2 \\| &lt;details&gt; \\`x\\`" in blockers, blockers


def test_a_publishable_package_says_so_and_has_no_blocker_table():
    text = tc_view.outcome_md([], [])
    assert text.startswith("**Publishable**") and "Blockers" not in text and "<details>" not in text


# ---------------------------------------------------------------- the pull request comment

class FakeApi:
    """GitHub's issue-comment endpoints, in memory."""

    def __init__(self, comments=None, refuse=None, me=None):
        self.repo, self.token = "o/r", "t"
        self.comments = comments or []
        self.refuse = refuse or set()
        self.me = me
        self.calls = []

    def call(self, method, path, body=None):
        self.calls.append((method, path))
        if method in self.refuse:
            raise urllib.error.HTTPError(path, 403, "Resource not accessible by integration",
                                         {}, io.BytesIO(b""))
        if method == "GET" and path == "/user":
            if self.me:
                return {"login": self.me}
            raise urllib.error.HTTPError(path, 403, "workflow token", {}, io.BytesIO(b""))
        if method == "GET":
            assert path.startswith("/repos/o/r/issues/3/comments?"), path
            page = int(re.search(r"[?&]page=(\d+)", path).group(1))
            return self.comments[(page - 1) * 100: page * 100]
        if method == "POST":
            c = {"id": len(self.comments) + 1, "body": body["body"],
                 "user": {"login": self.me or tc_view.BOT}}
            self.comments.append(c)
            return c
        cid = int(path.rsplit("/", 1)[1])
        next(c for c in self.comments if c["id"] == cid)["body"] = body["body"]
        return {}


def pr_env(tmp_path) -> dict:
    event = tmp_path / "event.json"
    event.write_text(json.dumps({"pull_request": {"number": 3, "head": {"sha": "feedface1"}}}))
    return {"GITHUB_EVENT_NAME": "pull_request", "GITHUB_EVENT_PATH": str(event),
            "GITHUB_REPOSITORY": "o/r", "GITHUB_RUN_ID": "9", "GITHUB_TOKEN": "t"}


def test_the_comment_is_created_once_then_updated_with_what_was_resolved(tmp_path):
    env = pr_env(tmp_path)
    api = FakeApi(comments=[{"id": 1000 + i, "body": "an unrelated comment"} for i in range(120)])
    first = [f("BLOCKER", "residue", "TODO at the end"), f("WARN", "md-links", "dual link")]
    assert tc_view.post_comment(first, tc_view.rows(first, None), "csd01", env, api).startswith("created")
    assert len(api.comments) == 121
    body = api.comments[-1]["body"]
    assert body.startswith(f"<!-- oasis-publication-checks: {tc_view.slot_for('csd01')} -->")
    assert "**Not publishable: 1 blocker, 1 warning**" in body and "Resolved" not in body
    assert "Checked commit feedfac" in body

    second = [f("WARN", "md-links", "dual link")]
    result = tc_view.post_comment(second, tc_view.rows(second, None), "csd01", env, api)
    assert result == f"updated comment {api.comments[-1]['id']}", result
    assert len(api.comments) == 121, "updated in place, not a second comment"
    body = api.comments[-1]["body"]
    assert "**Publishable (1 warning to review)**" in body
    resolved = body.split("Resolved since the last run (1)", 1)[1].split("<sub>")[0]
    assert "TODO at the end" in resolved and "dual link" not in resolved


def test_a_second_document_in_the_same_pull_request_gets_its_own_comment(tmp_path):
    env, api = pr_env(tmp_path), FakeApi()
    tc_view.post_comment([], [], "part 1", env, api)
    tc_view.post_comment([], [], "part 2", env, api)
    assert len(api.comments) == 2


def test_a_token_without_write_access_is_a_warning_not_a_failure(tmp_path, capsys, monkeypatch):
    env = pr_env(tmp_path)
    api = FakeApi(refuse={"POST"})
    result = tc_view.post_comment([f("BLOCKER")], tc_view.rows([f("BLOCKER")], None), "t", env, api)
    assert result.startswith("warning: ") and "pull-requests: write" in result, result

    report = tmp_path / "r.json"
    report.write_text(json.dumps({"target": "t", "findings": [f("BLOCKER")]}))
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    monkeypatch.setenv("GITHUB_API_URL", "http://127.0.0.1:9")   # nothing listens: refused
    assert tc_view.main(["comment", str(report)]) == 0
    assert capsys.readouterr().out.startswith("::warning title=Pull request comment not posted::")


def test_no_comment_outside_a_pull_request(tmp_path):
    env = pr_env(tmp_path)
    env["GITHUB_EVENT_NAME"] = "push"
    api = FakeApi()
    assert tc_view.post_comment([], [], "t", env, api).startswith("skipped")
    assert api.calls == []


def test_state_from_an_edited_comment_cannot_inject_markup():
    hostile = [{"k": "zz", "s": "BLOCKER", "c": "residue", "d": "<img src=x onerror=alert(1)> | x"}]
    blob = base64.b64encode(json.dumps(hostile).encode()).decode()
    previous = tc_view.decode_state(f"x <!-- oasis-publication-checks-state: {blob} -->")
    body = tc_view.comment_body([], [], "t", previous)
    gone = body.split("Resolved since the last run (1)", 1)[1]
    assert "<img" not in gone and "&lt;img src=x onerror=alert(1)&gt; \\| x" in gone
    assert tc_view.decode_state("<!-- oasis-publication-checks-state: !!notbase64 -->") == []


# ---------------------------------------------------------------- the action, end to end

def action_steps() -> list[dict]:
    return yaml.safe_load((REPO_ROOT / "action.yml").read_text())["runs"]["steps"]


def test_the_action_leads_with_the_outcome_and_marks_files_by_repository_path(tmp_path):
    """Runs the action's own step scripts as the runner does, on a CSAF
    package with a planted editor note: the summary opens with the outcome
    and the blocker, the report opens with it too, and the annotation names
    the file by its path in the repository and the line of the note."""
    steps = action_steps()
    gate = next(s["run"] for s in steps if s.get("id") == "pubcheck")
    annotate = next(s["run"] for s in steps if s.get("name") == "Mark the findings on the files")
    summary = next(s["run"] for s in steps if s.get("name") == "Write step summary")
    work, temp = tmp_path / "work", tmp_path / "runner-temp"
    temp.mkdir()
    stage = stage_from_corpus(work / "docs", CSAF_CSD01)
    md = stage / "csaf-v2.1-csd01.md"
    text = md.read_text().splitlines()
    text.insert(40, "TODO: rewrite this paragraph before the vote.")
    md.write_text("\n".join(text) + "\n")
    target = str(stage.relative_to(work))
    out, step_summary = tmp_path / "github-output", tmp_path / "summary.md"
    env = {"PATH": f"{Path(sys.executable).parent}:/usr/bin:/bin",
           "ACTION_PATH": str(REPO_ROOT), "TARGET": target, "EXTRA_ARGS": "",
           "REPORT_DIR": "pubcheck-report", "SUMMARY_TITLE": "",
           "RUNNER_TEMP": str(temp), "GITHUB_OUTPUT": str(out), "GITHUB_WORKSPACE": str(work),
           "GITHUB_STEP_SUMMARY": str(step_summary), "PUB_CHECK_OFFLINE": "1"}
    subprocess.run(["bash", "-c", gate], cwd=work, env=env, capture_output=True, text=True)
    outputs = dict(line.split("=", 1) for line in out.read_text().splitlines())
    assert outputs["exit_code"] == "1", outputs

    note = next(i for i, line in enumerate(md.read_text().splitlines(), 1)
                if line.startswith("TODO: rewrite"))
    result = subprocess.run(["bash", "--noprofile", "--norc", "-eo", "pipefail", "-c", annotate],
                            cwd=work, env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    errors = "\n".join(x for x in result.stdout.splitlines() if x.startswith("::error "))
    assert f"::error file={target}/csaf-v2.1-csd01.md,line={note}," in errors, result.stdout

    env["EXIT_CODE"] = outputs["exit_code"]
    result = subprocess.run(["bash", "--noprofile", "--norc", "-eo", "pipefail", "-c", summary],
                            cwd=work, env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    section = step_summary.read_text()
    lines = [x for x in section.splitlines() if x.strip()]
    assert lines[0].startswith("## OASIS publication checks: ")
    assert lines[2].startswith("**Not publishable: "), lines[:4]
    blockers = section.split("### Blockers: fix these", 1)[1].split("<details>", 1)[0]
    assert f"csaf-v2.1-csd01.md line {note} |" in blockers
    assert f"markdown line {note}: 'TODO:'" in blockers
    # The per-check tables are still there, collapsed, below the outcome.
    assert section.index("### Blockers") < section.index("Full findings list (ordered)") \
        < section.index("Every check class")

    report = (work / outputs["report_validation_md"]).read_text()
    head = report.split("## Report details", 1)[0]
    assert head.splitlines()[2].startswith("**Not publishable: ")
    assert f"markdown line {note}: 'TODO:'" in head
    page = (work / outputs["report_validation_html"]).read_text()
    assert page.index('class="outcome"') < page.index("Report details") < page.index("Check-by-Check")


def test_the_comment_step_runs_only_for_pull_requests_and_never_fails_the_job():
    step = next(s for s in action_steps() if s.get("name") == "Comment on the pull request")
    assert step.get("continue-on-error") is True
    cond = step["if"]
    assert "github.event_name == 'pull_request'" in cond and "inputs.pr-comment == 'auto'" in cond
    assert "exit_code != '2'" in cond
    inputs = yaml.safe_load((REPO_ROOT / "action.yml").read_text())["inputs"]
    assert inputs["pr-comment"]["default"] == "auto"
    assert inputs["annotations"]["default"] == "true"


def test_every_condition_override_names_a_registered_condition():
    """An override keyed on a signature the checker no longer emits would
    silently stop applying; each key must be a (class, signature, severity)
    the condition registry carries."""
    inventory = tc_view_conditions()
    for key in plain_language.CONDITIONS:
        assert key in inventory, f"no registered condition {key}"
    what, _ = plain_language.explain("front-matter", "x -- confirm this is an intentional external reference.", "WARN")
    assert what.startswith("The document links to a different version")
    assert plain_language.explain("front-matter", "This-stage URL points at", "BLOCKER") == \
        plain_language.PLAIN["front-matter"]


def tc_view_conditions() -> set[tuple[str, str, str]]:
    import oasis_pub_check
    return {(c["check"], c["sig"], c["severity"]) for c in oasis_pub_check.conditions_inventory()}


def test_a_finding_that_names_its_file_is_placed_at_the_value_it_quotes(tmp_path):
    stage = package(tmp_path)
    (stage / "schema" / "a.json").write_text('{\n  "title": "a",\n  "$id": "https://x.example/v9/a.json"\n}\n')
    pkg = tc_view.Package(str(stage))
    msg = "schema/a.json: $id is 'https://x.example/v9/a.json' but the file publishes under 'https://y/'."
    assert pkg.locate(f("BLOCKER", "schema-id", msg)) == ("schema/a.json", 3)


# ---------------------------------------------------------------- review counterexamples

def corpus_findings(stage: Path) -> list[dict]:
    env = dict(os.environ, PUB_CHECK_OFFLINE="1")
    out = subprocess.run([sys.executable, str(PUB / "oasis_pub_check.py"), str(stage), "--json"],
                         capture_output=True, text=True, env=env)
    return json.loads(out.stdout)["findings"]


def test_a_dual_link_is_placed_on_the_line_that_holds_the_link():
    """Review: the same address first appears as cover text ("Latest stage:
    https://.../aggregator.json"), and 52 of 64 dual-link rows landed there."""
    pkg = tc_view.Package(str(CSAF_CSD01))
    dual = [x for x in corpus_findings(CSAF_CSD01) if x["message"].startswith("Dual link")]
    assert len(dual) >= 5, dual
    for x in dual:
        rel, n = pkg.locate(x)
        url = x["message"].rsplit(": ", 1)[1]
        line = (CSAF_CSD01 / rel).read_text().split("\n")[n - 1]
        assert f"]({url})" in line, (n, url, line)


def test_the_located_file_is_the_one_the_checker_read():
    """Review: the largest PDF was a -DIFF PDF, and a larger comment
    resolution log took a TODO that was in the specification."""
    import oasis_pub_check
    stages = [p.parent for p in CORPUS.rglob("*.md") if p.parent.name[:2] in ("cs", "os", "cn")]
    assert len(stages) >= 5, stages
    for stage in set(stages):
        expected = {k: os.path.basename(v) for k, v in oasis_pub_check.find_delivery_items(str(stage)).items()}
        pkg = tc_view.Package(str(stage))
        for ext in ("md", "html", "pdf"):
            assert pkg.main(ext) == expected.get(ext), (stage, ext)


def test_a_todo_beside_a_larger_comment_log_is_placed_in_the_specification(tmp_path):
    stage = package(tmp_path)
    (stage / "x-v1.0-csd01-comment-resolution-log.md").write_text("big\n" * 5000)
    pkg = tc_view.Package(str(stage))
    assert pkg.locate(f("BLOCKER", message="Editor TODO left in markdown line 6: 'TODO:'")) == \
        ("x-v1.0-csd01.md", 6)


def test_a_finding_that_only_moved_is_not_resolved():
    a = [f("BLOCKER", "residue", "Editor TODO left in markdown line 8: 'TODO:'")]
    b = [f("BLOCKER", "residue", "Editor TODO left in markdown line 9: 'TODO:'")]
    previous = tc_view.decode_state(tc_view.comment_body(a, tc_view.rows(a, None, env={}), "t", None))
    body = tc_view.comment_body(b, tc_view.rows(b, None, env={}), "t", previous)
    assert "Resolved since" not in body


def test_a_dangling_link_in_the_stage_does_not_break_the_summary(tmp_path):
    """Review: os.path.getsize on a dangling symlink raised, and the summary
    step (which has no continue-on-error) failed a publishable run."""
    steps = action_steps()
    gate = next(s["run"] for s in steps if s.get("id") == "pubcheck")
    summary = next(s["run"] for s in steps if s.get("name") == "Write step summary")
    work, temp = tmp_path / "work", tmp_path / "rt"
    temp.mkdir()
    stage = stage_from_corpus(work / "d", CSAF_CSD01)
    os.symlink("missing.md", stage / "notes.md")
    out, step_summary = tmp_path / "out", tmp_path / "summary.md"
    env = {"PATH": f"{Path(sys.executable).parent}:/usr/bin:/bin", "ACTION_PATH": str(REPO_ROOT),
           "TARGET": str(stage.relative_to(work)), "EXTRA_ARGS": "", "REPORT_DIR": "r",
           "SUMMARY_TITLE": "", "RUNNER_TEMP": str(temp), "GITHUB_OUTPUT": str(out),
           "GITHUB_WORKSPACE": str(work), "GITHUB_STEP_SUMMARY": str(step_summary),
           "PUB_CHECK_OFFLINE": "1"}
    subprocess.run(["bash", "-c", gate], cwd=work, env=env, capture_output=True, text=True)
    outputs = dict(line.split("=", 1) for line in out.read_text().splitlines())
    assert outputs["report_validation_md"], "the report must still render"
    env["EXIT_CODE"] = outputs["exit_code"]
    result = subprocess.run(["bash", "--noprofile", "--norc", "-eo", "pipefail", "-c", summary],
                            cwd=work, env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert "## OASIS publication checks: " in step_summary.read_text()


def test_each_todo_is_its_own_finding_on_its_own_line():
    """The residue check now names each marker's line, so two markers are two
    blockers (they were merged into one identical message before v1.15.0)."""
    import oasis_pub_check
    found = oasis_pub_check.Findings()
    md = "# T\n\n```\nTODO: in code, ignored\n```\n\nTODO: one\n\nText `TODO:` inline.\nTODO: two\n"
    oasis_pub_check.check_residue(md, "", found)
    todo = [x["message"] for x in found.items if "TODO" in x["message"]]
    assert todo == ["Editor TODO left in markdown line 7: 'TODO:'",
                    "Editor TODO left in markdown line 10: 'TODO:'"], todo


def test_a_finding_that_opens_with_its_line_is_placed_there(tmp_path):
    pkg = tc_view.Package(str(package(tmp_path)))
    assert pkg.locate(f("BLOCKER", "fence-collapse", "Line 6: opening fence info string carries trailing "
                        "text ('json title=...')")) == ("x-v1.0-csd01.md", 6)


def test_same_as_above_only_when_the_wording_is_the_same():
    fs = [f("BLOCKER", "schema-id", "a.json is not valid JSON (line 1)"),
          f("BLOCKER", "schema-id", "b.json: $ref 'x' disagrees with $id 'y'")]
    text = tc_view.outcome_md(fs, tc_view.rows(fs, None, env={}))
    assert "Same as above" not in text and "not valid JSON." in text and "own <span>$</span>id" in text


def test_a_comment_someone_else_wrote_with_the_marker_is_left_alone(tmp_path):
    env = pr_env(tmp_path)
    marker = tc_view.MARKER.format(slot=tc_view.slot_for("t"))
    api = FakeApi(comments=[{"id": 5, "body": marker + " pasted by a reviewer",
                             "user": {"login": "someone"}}])
    assert tc_view.post_comment([], [], "t", env, api).startswith("created")
    assert api.comments[0]["body"].endswith("pasted by a reviewer")
    assert ("PATCH", "/repos/o/r/issues/comments/5") not in api.calls


def test_a_personal_token_finds_the_comment_it_wrote(tmp_path):
    env = pr_env(tmp_path)
    api = FakeApi(me="editor")
    tc_view.post_comment([], [], "t", env, api)
    assert tc_view.post_comment([], [], "t", env, api).startswith("updated")


def test_malformed_state_in_an_edited_comment_is_dropped():
    for items in ([{"k": "a", "s": "BLOCKER", "c": ["x"], "d": ""}], {"k": "a"}, "x", [1, None]):
        blob = base64.b64encode(json.dumps(items).encode()).decode()
        assert tc_view.decode_state(f"<!-- oasis-publication-checks-state: {blob} -->") == []


def test_a_check_that_did_not_run_is_not_described_as_a_defect():
    msg = ("NOT EVALUATED: the files the spec cites under its own stage path could not be checked "
           "against the package: the cover's This-stage block gave no base URL for this package's "
           "/v1.0/csd01/ directory.")
    what, fix = plain_language.explain("package-refs", msg, "BLOCKER")
    assert what.startswith("This check could not run") and "This version" in fix
    assert plain_language.explain("x", "NOT EVALUATED: something else", "WARN")[0].startswith(
        "This check could not run")


def test_the_comment_fits_githubs_limit_whatever_the_number_of_findings():
    fs = [f("BLOCKER" if i % 2 else "WARN", "residue", f"finding {i} " + "x" * 200) for i in range(3000)]
    body = tc_view.comment_body(fs, tc_view.rows(fs, None, env={}), "t", None)
    assert len(body) <= 65_536, len(body)
    assert tc_view.decode_state(body), "some state is still carried"


def test_line_numbers_count_lf_only(tmp_path):
    stage = package(tmp_path)
    md = stage / "x-v1.0-csd01.md"
    md.write_text("a\u2028b\fc\nsee [https://e.org/q](https://e.org/q)\n")
    pkg = tc_view.Package(str(stage))
    assert pkg.locate(f("WARN", "md-links", "Dual link: https://e.org/q")) == ("x-v1.0-csd01.md", 2)


def test_titles_that_read_alike_get_separate_comments():
    assert tc_view.slot_for("csaf v2.1") != tc_view.slot_for("csaf-v2.1")
    assert tc_view.slot_for("a" * 200 + "1") != tc_view.slot_for("a" * 200 + "2")


def test_the_unreadable_target_summary_escapes_the_title(tmp_path):
    summary = next(s["run"] for s in action_steps() if s.get("name") == "Write step summary")
    step_summary = tmp_path / "summary.md"
    env = {"PATH": f"{Path(sys.executable).parent}:/usr/bin:/bin", "ACTION_PATH": str(REPO_ROOT),
           "EXIT_CODE": "2", "TARGET": "x`y", "SUMMARY_TITLE": "**pwned** <img src=x onerror=1>",
           "GITHUB_STEP_SUMMARY": str(step_summary), "REPORT_DIR": "", "RUNNER_TEMP": str(tmp_path)}
    result = subprocess.run(["bash", "--noprofile", "--norc", "-eo", "pipefail", "-c", summary],
                            cwd=tmp_path, env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    text = step_summary.read_text()
    assert text.startswith("## OASIS publication checks: \\*\\*pwned\\*\\* &lt;img"), text
    assert "The target could not be read (exit code 2)" in text and "`` x`y ``" in text


def test_invalid_json_is_placed_where_the_parser_stopped(tmp_path):
    stage = package(tmp_path)
    (stage / "schema" / "a.json").write_text('{\n  "a": 1\n  "b": 2\n}\n')
    try:
        json.loads((stage / "schema" / "a.json").read_text())
    except ValueError as exc:
        msg = f"schema/a.json: not valid JSON ({exc})"
    assert tc_view.Package(str(stage)).locate(f("BLOCKER", "schema-id", msg)) == ("schema/a.json", 3)
