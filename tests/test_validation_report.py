"""The full Validation Report covers every check the tool carries.

pub-check/validation_report.py turns one --json run into the per-check report
the composite action publishes beside the findings list. Its value is
completeness: a TC reading it must see every check class and every individual
condition, including the ones that passed or did not apply. These tests read
the RENDERED report files, not the record behind them, and compare them with
the inventory --list-checks prints, which is derived from the checker's AST.
"""

from __future__ import annotations

import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest

from conftest import CORPUS, REPO_ROOT, run_cli, stage_from_corpus

REPORT = REPO_ROOT / "pub-check" / "validation_report.py"
CSAF_CSD01 = CORPUS / "csaf" / "v2.1" / "csd01"


def list_checks() -> dict[str, int]:
    """Class name -> condition count, as --list-checks prints it."""
    result = run_cli("--list-checks")
    assert result.returncode == 0, result.stderr
    inventory = {m.group(1): int(m.group(2))
                 for m in re.finditer(r"(?m)^  ([a-z0-9-]+)\s+(\d+)$", result.stdout)}
    total = re.search(r"(\d+) individual checks across (\d+) check classes", result.stdout)
    assert total, result.stdout
    assert len(inventory) == int(total.group(2)), "could not parse every class line"
    assert sum(inventory.values()) == int(total.group(1))
    return inventory


def table_rows(md: str, heading: str) -> list[list[str]]:
    """The body rows of the first table under `heading`, split into cells on
    unescaped pipes."""
    section = md.split(heading, 1)[1]
    rows = []
    for line in section.splitlines():
        if re.match(r"^\| \d+ \|", line):
            rows.append([c.strip() for c in re.split(r"(?<!\\)\|", line)[1:-1]])
        elif rows and not line.startswith("|"):
            break
    return rows


@pytest.fixture(scope="module")
def report(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("validation")
    stage = stage_from_corpus(tmp / "pkg", CSAF_CSD01)
    gate = run_cli("--json", str(stage))
    assert gate.returncode in (0, 1), gate.stderr
    (tmp / "r.json").write_text(gate.stdout)
    md, html = tmp / "pubcheck-validation.md", tmp / "pubcheck-validation.html"
    result = subprocess.run(
        [sys.executable, str(REPORT), str(tmp / "r.json"), "--md", str(md),
         "--html", str(html), "--exit-code", str(gate.returncode)],
        capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    return md.read_text(), html.read_text()


def test_every_check_class_and_condition_appears_exactly_once(report):
    md, html = report
    inventory = list_checks()

    classes = [row[2] for row in table_rows(md, "## Check-by-Check Results")]
    assert Counter(classes) == Counter(inventory.keys()), (
        f"class table differs from --list-checks: missing "
        f"{sorted(set(inventory) - set(classes))}, duplicated "
        f"{sorted(k for k, n in Counter(classes).items() if n > 1)}, extra "
        f"{sorted(set(classes) - set(inventory))}")

    conditions = table_rows(md, "## All Individual Conditions")
    assert len(conditions) == sum(inventory.values())
    assert Counter(row[2] for row in conditions) == Counter(inventory), (
        "condition table's per-class counts differ from --list-checks")
    assert all(row[1].split(" ")[0] in {"PASS", "WARN", "BLOCKER", "NA"} for row in conditions)
    assert all(len(row) == 6 for row in conditions), "a cell value broke the table"

    html_classes = re.findall(r'<td><code>([a-z0-9-]+)</code></td><td class="n">\d+</td>', html)
    assert Counter(html_classes) == Counter(inventory.keys())


def test_a_pipe_in_an_observed_value_stays_inside_its_cell(tmp_path):
    """Observed values and finding messages are free text from the package.
    A literal pipe must not split a Markdown table cell."""
    data = ('{"target": "t", "blockers": 1, "observed": {"x": {"k": "a|b"}},'
            ' "findings": [{"severity": "BLOCKER", "check": "x", "message": "sig p|q"}],'
            ' "conditions": [{"check": "x", "sig": "sig", "applies": "all",'
            ' "condition": "c", "pulls": "p", "compares_to": "e|f"}]}')
    (tmp_path / "r.json").write_text(data)
    md = tmp_path / "o.md"
    result = subprocess.run([sys.executable, str(REPORT), str(tmp_path / "r.json"),
                             "--md", str(md)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    rows = table_rows(md.read_text(), "## All Individual Conditions")
    assert len(rows) == 1 and len(rows[0]) == 6, rows
    assert rows[0][1] == "BLOCKER" and "p\\|q" in rows[0][4]


def render(tmp_path, data: dict) -> str:
    import json
    (tmp_path / "r.json").write_text(json.dumps(data))
    md = tmp_path / "o.md"
    result = subprocess.run([sys.executable, str(REPORT), str(tmp_path / "r.json"),
                             "--md", str(md)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    return md.read_text()


def condition(**kw) -> dict:
    return {"check": "x", "sig": "sig", "applies": "all", "condition": "c",
            "pulls": "p", "compares_to": "e", **kw}


def test_a_blocker_is_never_hidden_behind_an_na_reason(tmp_path):
    """Red-team counterexample: a Previous-stage URI 404 fired a BLOCKER in
    stage-uri-live while revision-collision, which the network NA rule looks
    for, had skipped silently. The row read 'NA: live-site probe skipped'."""
    md = render(tmp_path, {
        "target": "t", "blockers": 1, "observed": {},
        "findings": [{"severity": "BLOCKER", "check": "x", "message": "sig: HTTP 404"}],
        "conditions": [condition(requires="network")]})
    rows = table_rows(md, "## All Individual Conditions")
    assert rows[0][1] == "BLOCKER", rows


def test_a_condition_the_checker_did_not_evaluate_is_not_pass(tmp_path):
    """Red-team counterexample: title-version emitted only INFO 'Not
    evaluated: blocked by an upstream html-residue defect', and all three of
    its conditions read PASS."""
    md = render(tmp_path, {
        "target": "t", "blockers": 0, "observed": {"x": {"k": "v"}},
        "findings": [{"severity": "INFO", "check": "x",
                      "message": "Not evaluated: blocked by an upstream defect."}],
        "conditions": [condition(), condition(sig="other", condition="d")]})
    rows = table_rows(md, "## All Individual Conditions")
    assert [r[1] for r in rows] == ["NA", "NA"], rows
    assert "Not evaluated" in rows[0][4]


def test_package_markup_in_a_finding_is_not_rendered(tmp_path):
    """Red-team counterexample: a file named with <details> collapsed the rest
    of its class cell behind a toggle in the rendered Markdown."""
    md = render(tmp_path, {
        "target": "t", "blockers": 1, "observed": {},
        "findings": [{"severity": "BLOCKER", "check": "x", "message": "sig in <details>.html"}],
        "conditions": [condition()]})
    body = md.split("## Check-by-Check Results", 1)[1]
    assert "<details>" not in body
    assert "&lt;details&gt;.html" in body


def test_a_failed_render_leaves_no_earlier_report_in_report_dir(tmp_path):
    """Red-team counterexample: two action calls in one job share report-dir.
    When the second call's report cannot be rendered, the first call's
    pubcheck-validation.md/.html must not survive beside its findings.
    Runs the gate step's own script from action.yml."""
    import yaml
    steps = yaml.safe_load((REPO_ROOT / "action.yml").read_text())["runs"]["steps"]
    script = next(s["run"] for s in steps if s.get("id") == "pubcheck")
    stage = stage_from_corpus(tmp_path / "pkg", CSAF_CSD01)
    work, temp = tmp_path / "work", tmp_path / "runner-temp"
    work.mkdir()
    temp.mkdir()

    def call(target: str) -> dict:
        out = tmp_path / "github-output"
        out.write_text("")
        env = {"PATH": f"{Path(sys.executable).parent}:/usr/bin:/bin",
               "ACTION_PATH": str(REPO_ROOT), "TARGET": target, "EXTRA_ARGS": "",
               "REPORT_DIR": "pubcheck-report", "SUMMARY_TITLE": "",
               "RUNNER_TEMP": str(temp), "GITHUB_OUTPUT": str(out),
               "PUB_CHECK_OFFLINE": "1"}
        subprocess.run(["bash", "-c", script], cwd=work, env=env,
                       capture_output=True, text=True)
        return dict(line.split("=", 1) for line in out.read_text().splitlines())

    first = call(str(stage))
    assert first["report_validation_md"] == "pubcheck-report/pubcheck-validation.md"
    assert (work / first["report_validation_md"]).stat().st_size > 0

    second = call(str(tmp_path / "missing" / "v9.9" / "csd99"))
    assert second["report_validation_md"] == "" and second["report_validation_html"] == ""
    assert second["report_validation_pdf"] == ""
    assert not (work / "pubcheck-report" / "pubcheck-validation.md").exists()
    assert not (work / "pubcheck-report" / "pubcheck-validation.html").exists()
    assert not (work / "pubcheck-report" / "pubcheck-validation.pdf").exists()


def test_a_live_check_that_could_not_reach_the_site_is_not_pass(tmp_path):
    """Red-team round 2: with the network down, stage-uri-live reported only
    INFO 'could not be reached' and revision-collision recorded
    '(unreachable)'; every live-site row read PASS."""
    md = render(tmp_path, {
        "target": "t", "blockers": 0,
        "observed": {"revision-collision": {"http_status": "(unreachable)"},
                     "x": {"previous_stage_urls": "https://example.org/a.html"}},
        "findings": [{"severity": "INFO", "check": "x", "message":
                      "Previous stage URI could not be reached to confirm it retrieves "
                      "(transport failure, not a 404): https://example.org/a.html."}],
        "conditions": [condition(requires="network"), condition(check="y", sig="s2")]})
    rows = table_rows(md, "## All Individual Conditions")
    assert [r[1] for r in rows] == ["NA", "PASS"], rows


def test_document_text_quoted_in_a_finding_does_not_mark_a_check_unevaluated(tmp_path):
    """Red-team round 2: an appendix heading 'Tests skipped in this release',
    quoted in an INFO, turned a condition that scanned 374 headings into
    'NA: not evaluated'. So did a file name such as skipped.html."""
    md = render(tmp_path, {
        "target": "t", "blockers": 0, "observed": {"x": {"headings_scanned": "374"}},
        "findings": [
            {"severity": "INFO", "check": "x", "message":
             "Appendix/Annex heading 'Appendix Z. Tests skipped in this release' "
             "carries no content-type label."},
            {"severity": "INFO", "check": "x", "message": "Junk file skipped.html noted."}],
        "conditions": [condition(sig="unrelated")]})
    rows = table_rows(md, "## All Individual Conditions")
    assert rows[0][1] == "PASS", rows


def test_an_unreadable_input_marks_the_rest_of_its_class_unevaluated(tmp_path):
    """Red-team round 2: a corrupt PDF raised one pdf-sync BLOCKER ('could
    not read the PDF') and the check returned; its other conditions read
    PASS although nothing was compared."""
    md = render(tmp_path, {
        "target": "t", "blockers": 1, "observed": {},
        "findings": [{"severity": "BLOCKER", "check": "x",
                      "message": "sig: pdftotext could not read the PDF (exit 1)"}],
        "conditions": [condition(), condition(sig="other", condition="d")]})
    rows = table_rows(md, "## All Individual Conditions")
    assert [r[1] for r in rows] == ["BLOCKER", "NA"], rows


def test_a_summary_title_starting_with_a_dash_still_renders(tmp_path):
    """Red-team rounds 2 and 3: action.yml passed --title "$SUMMARY_TITLE",
    and a title such as --csd01 was rejected by the argument parser, first in
    validation_report.py and then in render_summary.py, whose failure under
    bash -e stopped the step before the validation tables were written.
    Runs both of the action's own scripts as the runner does."""
    import yaml
    steps = yaml.safe_load((REPO_ROOT / "action.yml").read_text())["runs"]["steps"]
    gate = next(s["run"] for s in steps if s.get("id") == "pubcheck")
    summary = next(s["run"] for s in steps if s.get("name") == "Write step summary")
    stage = stage_from_corpus(tmp_path / "pkg", CSAF_CSD01)
    work, temp = tmp_path / "work", tmp_path / "runner-temp"
    work.mkdir()
    temp.mkdir()
    out, step_summary = tmp_path / "github-output", tmp_path / "summary.md"
    env = {"PATH": f"{Path(sys.executable).parent}:/usr/bin:/bin",
           "ACTION_PATH": str(REPO_ROOT), "TARGET": str(stage), "EXTRA_ARGS": "",
           "REPORT_DIR": "pubcheck-report", "SUMMARY_TITLE": "--csd01",
           "RUNNER_TEMP": str(temp), "GITHUB_OUTPUT": str(out),
           "GITHUB_STEP_SUMMARY": str(step_summary), "PUB_CHECK_OFFLINE": "1"}
    subprocess.run(["bash", "-c", gate], cwd=work, env=env, capture_output=True, text=True)
    outputs = dict(line.split("=", 1) for line in out.read_text().splitlines())
    assert (work / outputs["report_validation_md"]).read_text().startswith(
        "# Publication Validation Report (pub-check): --csd01")

    env["EXIT_CODE"] = outputs["exit_code"]
    result = subprocess.run(["bash", "--noprofile", "--norc", "-eo", "pipefail", "-c", summary],
                            cwd=work, env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert "### Validation report: --csd01" in step_summary.read_text()


def test_a_live_check_that_reached_the_site_is_not_marked_offline(tmp_path):
    """Red-team round 3: on a live run where revision-collision recorded
    nothing but stage-uri-live fetched four URIs and all retrieved, the row
    read 'live-site probe could not run'."""
    md = render(tmp_path, {
        "target": "t", "blockers": 0,
        "observed": {"x": {"previous_stage_urls": "https://example.org/a.html",
                           "stage_uris_fetched": "4"}},
        "findings": [], "conditions": [condition(requires="network")]})
    rows = table_rows(md, "## All Individual Conditions")
    assert rows[0][1] == "PASS", rows


def test_a_stage_directory_that_could_not_be_scanned_is_not_pass(tmp_path):
    """Red-team round 3: public-review-metadata said the live stage directory
    'could not be scanned this run' and returned; its conditions read PASS,
    one of them claiming the directory was scanned."""
    md = render(tmp_path, {
        "target": "t", "blockers": 0,
        "observed": {"x": {"http_status": "403"}},
        "findings": [{"severity": "INFO", "check": "x", "message":
                      "csd01 underwent a TC public review but the live stage directory "
                      "https://example.org/csd01/ could not be scanned this run (http "
                      "status 403); cannot confirm whether the file is present."}],
        "conditions": [condition(requires="network"), condition(sig="b", condition="d")]})
    rows = table_rows(md, "## All Individual Conditions")
    assert [r[1] for r in rows] == ["NA", "NA"], rows


def test_a_stage_uri_answering_403_or_5xx_is_not_pass(tmp_path):
    """Red-team round 4: a Previous-stage URI answering HTTP 503 raised only
    INFO 'returned HTTP 503 (not a definitive 404)', and the condition
    'Every Previous-stage and Latest-stage URI actually retrieves' read PASS."""
    md = render(tmp_path, {
        "target": "t", "blockers": 0,
        "observed": {"x": {"stage_uris_fetched": "4"}},
        "findings": [{"severity": "INFO", "check": "x", "message":
                      "Previous stage URI returned HTTP 503 (not a definitive 404): "
                      "https://example.org/a.html. Confirm in a browser."}],
        "conditions": [condition(requires="network")]})
    rows = table_rows(md, "## All Individual Conditions")
    assert rows[0][1] == "NA", rows


def test_a_package_without_a_pdf_is_not_blamed_on_the_toolchain(tmp_path):
    """Red-team round 5: a package with no PDF gave every PDF condition the
    reason 'pdftotext (poppler) unavailable on this runner', which is false."""
    md = render(tmp_path, {
        "target": "t", "blockers": 1,
        "observed": {"filenames": {"formats_present": "html, md"}},
        "findings": [{"severity": "BLOCKER", "check": "filenames",
                      "message": "Missing delivery format(s): pdf"}],
        "conditions": [condition(requires="pdftotext"), condition(requires="pdffonts", sig="f")]})
    rows = table_rows(md, "## All Individual Conditions")
    assert [r[1] for r in rows] == ["NA", "NA"], rows
    assert all("no PDF in the package" in r[4] for r in rows), rows


def render_all(tmp_path, data: dict) -> tuple[str, str, str]:
    """The Markdown report, the HTML report and the step summary for one run:
    the three surfaces the class table is printed on (the PDF is the HTML)."""
    import json
    (tmp_path / "r.json").write_text(json.dumps(data))
    md, page, summary = tmp_path / "o.md", tmp_path / "o.html", tmp_path / "summary.md"
    result = subprocess.run([sys.executable, str(REPORT), str(tmp_path / "r.json"),
                             "--md", str(md), "--html", str(page), "--step-summary"],
                            capture_output=True, text=True,
                            env={"PATH": "/usr/bin:/bin", "GITHUB_STEP_SUMMARY": str(summary)})
    assert result.returncode == 0, result.stderr
    return md.read_text(), page.read_text(), summary.read_text()


def class_results(text: str) -> dict[str, list[str]]:
    return {r[2]: r for r in table_rows(text, "Check-by-Check Results" if "## Check" in text
                                        else "| # | Result | Check class")}


def test_a_class_whose_every_condition_is_na_reads_na_with_its_reason(tmp_path):
    """Adoption walkthrough: with PUB_CHECK_OFFLINE=1, public-review-metadata
    and revision-collision read 'PASS | 3 | none' in the class table while
    every one of their conditions was NA. A class that checked nothing is NA
    and says why, in the report and in the step summary."""
    md, page, summary = render_all(tmp_path, {
        "target": "t", "blockers": 0,
        "observed": {"revision-collision": {"http_status": "(unreachable)"}},
        "findings": [],
        "conditions": [condition(check="x", sig="a", requires="network"),
                       condition(check="x", sig="b", requires="network"),
                       condition(check="y", sig="d")]})
    for text in (md, summary):
        rows = class_results(text)
        assert rows["x"][1] == "NA", rows
        assert "no live-site result" in rows["x"][4], rows
        assert rows["y"][1] == "PASS", rows
    assert '<td class="r NA">NA</td><td><code>x</code>' in page


def test_a_partly_evaluated_class_says_how_much_was_evaluated(tmp_path):
    """Offline CSAF v2.1: uri-alias ran 6 of its 9 conditions and read a bare
    PASS, as though all nine had been compared."""
    md, _, _ = render_all(tmp_path, {
        "target": "t", "blockers": 0, "observed": {},
        "findings": [{"severity": "WARN", "check": "w", "message": "sig: bad"}],
        "conditions": [condition(check="x", sig="a", requires="network"),
                       condition(check="x", sig="b"), condition(check="x", sig="c"),
                       condition(check="w", sig="other", requires="network"),
                       condition(check="w")]})
    rows = class_results(md)
    assert rows["x"][1] == "PASS (2 of 3 evaluated)", rows
    assert rows["w"][1] == "WARN (1 of 2 evaluated)", rows


def test_a_finding_outranks_an_all_na_class(tmp_path):
    """No NA reason may hide a finding: a class whose conditions all read NA
    but which raised a WARN reads WARN."""
    md, _, _ = render_all(tmp_path, {
        "target": "t", "blockers": 0, "observed": {},
        "findings": [{"severity": "WARN", "check": "x", "message": "unmatched text"}],
        "conditions": [condition(requires="network")]})
    rows = class_results(md)
    assert rows["x"][1].split()[0] == "WARN", rows
    assert "unmatched text" in rows["x"][4], rows


def test_the_summary_line_counts_only_evaluated_classes_as_clean(tmp_path):
    """Offline CSAF v2.1 said '49 of 59 check classes fully clean' while five
    of the 49 had evaluated nothing."""
    md, page, summary = render_all(tmp_path, {
        "target": "t", "blockers": 0,
        "observed": {"revision-collision": {"http_status": "(unreachable)"}},
        "findings": [{"severity": "INFO", "check": "z", "message": "noted"}],
        "conditions": [condition(check="x", requires="network"),
                       condition(check="y"), condition(check="z")]})
    line = "1 of 2 evaluated check classes fully clean; 1 not evaluated;"
    assert line in md and line in page and line in summary, md


def test_a_finding_under_a_class_with_no_conditions_appears_in_the_class_table(tmp_path):
    """csaf-cvrf v1.2 cs01: the 'track' INFO (Word-authored package) belongs
    to a class with no registered conditions and appeared in no table."""
    md, page, summary = render_all(tmp_path, {
        "target": "t", "blockers": 0, "observed": {},
        "findings": [{"severity": "INFO", "check": "track", "message": "Word-authored package"}],
        "conditions": [condition()]})
    for text in (md, summary):
        rows = class_results(text)
        assert rows["track"][1] == "INFO" and rows["track"][3] == "0", rows
        assert "Word-authored package" in rows["track"][4], rows
    assert "<code>track</code>" in page
