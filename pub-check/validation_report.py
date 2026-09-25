#!/usr/bin/env python3
# Copyright 2026 OASIS Open
# SPDX-License-Identifier: Apache-2.0
# Authored by Michael Coletta, Technical Advisor to OASIS Open.
"""Render the full per-check Validation Report from one oasis_pub_check.py --json run.

The findings list says what failed. This report says what was checked: every
check class the tool carries and every individual condition inside it, each
with its result (PASS, WARN, BLOCKER or NA), the value the check pulled from
the package, and what that value was compared against. It is the same report
OASIS staff produce at intake, so a TC's CI and the staff record read alike.

Nothing is truncated in the condition table: the observed value is the
evidence the table exists to show. The class table caps each class at five
findings and points at the JSON record for the rest.

Usage:
  validation_report.py <report.json> --md <out.md> [--html <out.html>]
                       [--title <label>] [--exit-code N] [--date YYYY-MM-DD]
                       [--step-summary [--report-files <text>]]

<report.json> is the output of `oasis_pub_check.py --json <target>`.
--step-summary also appends the class table, and the condition table in a
collapsed section, to $GITHUB_STEP_SUMMARY (stdout when that is unset).

Standard library only. Exit 0 on success, 2 when the input is not a pub-check
--json report.
"""
from __future__ import annotations

import argparse
import datetime
import html
import json
import os
import re
import sys

SEV_ORDER = {"BLOCKER": 0, "WARN": 1, "INFO": 2}
RENDER_CAP = 5          # findings shown per class in the class table
SUMMARY_LIMIT = 900_000  # GitHub refuses a step summary over 1 MiB
TOOL = "oasis_pub_check.py (OASIS-Docs/publication-assurance)"


def class_inventory(conditions: list[dict]) -> list[dict]:
    """Every check class with its condition count, sorted by name. The
    --json report emits every documented condition on every run, so this is
    the same inventory --list-checks prints."""
    counts: dict[str, int] = {}
    for c in conditions:
        counts[c["check"]] = counts.get(c["check"], 0) + 1
    return [{"check": k, "conditions": counts[k]} for k in sorted(counts)]


def probed(obs: dict) -> bool:
    """Whether a live-site check's own observation shows it reached the site:
    an HTTP status other than '(unreachable)', or a non-zero count of fetched
    URIs. Offline runs record neither."""
    status = obs.get("http_status")
    fetched = obs.get("stage_uris_fetched")
    return (status not in (None, "", "(unreachable)")
            or fetched not in (None, "", "0"))


def not_applicable(c: dict, observed: dict, has_md: bool, formats: str) -> str | None:
    """Why a condition does not apply to this package, or None. NA is driven
    by the source formats the package carries and by absent prerequisites,
    never by a silent pass."""
    cond = c["condition"]
    if c["applies"] == "md" and not has_md:
        return "NA: markdown-source condition; this package carries no markdown source"
    if c["applies"] == "docx" and "docx" not in formats:
        return "NA: DOCX-render condition; this package carries no Word source"
    if c["applies"] == "odt" and "odt-integrity" not in observed:
        return "NA: ODT-source condition; this package carries no ODT source"
    if cond.endswith("(markdown source)") and not has_md:
        return "NA: evaluated on the HTML-render row for this package"
    if cond.endswith("(HTML render)") and has_md:
        return "NA: evaluated on the markdown-source row for this package"
    req = c.get("requires")
    if req == "schemas" and observed.get("schema-id", {}).get("json_files", "0") in ("0", None):
        return "NA: no JSON schema files in the package"
    if req == "manifest" and observed.get("manifest", {}).get("manifest_json") != "present":
        return "NA: no manifest.json in the package (noted as informational)"
    if req == "network" and not probed(observed.get(c["check"], {})):
        return "NA: no live-site result for this check (offline, unreachable, or nothing to probe)"
    if req == "pdftotext" and "pdf-sync" not in observed and "pdf-cover" not in observed:
        return "NA: pdftotext (poppler) unavailable on this runner"
    if req == "pdffonts" and "pdf-fonts" not in observed:
        return "NA: pdffonts unavailable or the package declares no font authority"
    return None


# The checker's own words for "this was not evaluated on this package".
NOT_EVALUATED = ("not evaluated", "skipped", "could not be reached", "could not confirm",
                 "could not be scanned", "not a definitive 404")
UNREADABLE = ("could not read", "could not be read")


def unquoted(msg: str) -> str:
    """A finding message without the package text it quotes: quoted spans,
    URLs and file names. A heading called 'Tests skipped in this release'
    is the document talking, not the checker."""
    msg = re.sub(r"https?://\S+", " ", msg)
    msg = re.sub(r"'[^']*'|\"[^\"]*\"", " ", msg)
    return re.sub(r"\S+\.[A-Za-z0-9]{1,5}\b", " ", msg).lower()


def skipped_reason(check: str, findings: list[dict]) -> str | None:
    """The checker's own statement that it did not evaluate a class on this
    package, or None: an INFO saying "Not evaluated", "... skipped", "could
    not be reached", "Could not confirm", "could not be scanned" or "not a
    definitive 404" (a 403 or 5xx), or a
    finding of any severity
    saying its input could not be read. A condition that was never
    evaluated must not read as PASS."""
    for f in findings:
        if f["check"] != check:
            continue
        text = unquoted(f["message"])
        phrases = NOT_EVALUATED + UNREADABLE if f["severity"] == "INFO" else UNREADABLE
        if any(p in text for p in phrases):
            return f"NA: not evaluated on this package: {f['message']}"
    return None


def condition_rows(data: dict) -> list[dict]:
    """One row per individual condition: result, the value pulled, and what
    it was compared against. A finding is attributed to a condition when it
    belongs to the same class and carries that condition's signature text.
    A BLOCKER or WARN always wins: no NA reason is allowed to hide one."""
    findings, observed = data["findings"], data.get("observed", {})
    formats = observed.get("filenames", {}).get("formats_present", "")
    has_md = "md" in formats
    rows = []
    for c in data["conditions"]:
        fired = [f for f in findings
                 if f["severity"] != "INFO" and f["check"] == c["check"] and c["sig"] in f["message"]]
        # The markdown-source and HTML-render twins of a condition share a
        # signature; a finding belongs to the row for the format evaluated.
        twin = c["condition"].endswith(("(markdown source)", "(HTML render)"))
        na = not_applicable(c, observed, has_md, formats)
        if na and twin:
            fired = []
        if fired:
            result = fired[0]["severity"] + (f" x{len(fired)}" if len(fired) > 1 else "")
            shown = [f["message"] for f in fired[:3]]
            if len(fired) > 3:
                shown.append(f"... and {len(fired) - 3} more (full list in the JSON record)")
            pulled = " | ".join(shown)
        elif na or skipped_reason(c["check"], findings):
            result, pulled = "NA", na or skipped_reason(c["check"], findings)
        else:
            result = "PASS"
            obs = observed.get(c["check"], {})
            pulled = ("; ".join(f"{k}: {v}" for k, v in obs.items())
                      or f"pulled: {c['pulls']}; no violating instance found")
        rows.append({"check": c["check"], "condition": c["condition"], "result": result,
                     "observed": pulled, "compares_to": c["compares_to"]})
    return rows


def build_record(data: dict, title: str, exit_code: int | None, date: str) -> dict:
    by_class: dict[str, list[dict]] = {}
    for f in data["findings"]:
        by_class.setdefault(f["check"], []).append(f)
    classes = []
    for item in class_inventory(data["conditions"]):
        fs = sorted(by_class.get(item["check"], []), key=lambda f: SEV_ORDER.get(f["severity"], 9))
        classes.append({"check": item["check"], "conditions": item["conditions"],
                        "result": fs[0]["severity"] if fs else "PASS",
                        "findings": [{"severity": f["severity"], "message": f["message"]}
                                     for f in fs]})
    sev = {s: sum(1 for f in data["findings"] if f["severity"] == s)
           for s in ("BLOCKER", "WARN", "INFO")}
    return {
        "title": title or data.get("target", "package"),
        "target": data.get("target", ""),
        "date": date, "tool": TOOL, "exit_code": exit_code,
        "total_checks": len(data["conditions"]), "total_classes": len(classes),
        "classes_clean": sum(1 for c in classes if not c["findings"]),
        "blockers": sev["BLOCKER"], "severity_counts": sev,
        "publication_ready": sev["BLOCKER"] == 0,
        "classes": classes, "condition_detail": condition_rows(data),
    }


def capped(findings: list[dict]) -> list[str]:
    msgs = [f"{f['severity']}: {f['message']}" for f in findings]
    if len(msgs) > RENDER_CAP:
        msgs = msgs[:RENDER_CAP] + [f"... and {len(msgs) - RENDER_CAP} more findings of this "
                                    "class (full list in the JSON record)"]
    return msgs


def verdict(rec: dict) -> str:
    return ("PUBLICATION-READY: zero blockers." if rec["publication_ready"]
            else f"NOT publication-ready: {rec['blockers']} blocker(s).")


def result_line(rec: dict) -> str:
    sc = rec["severity_counts"]
    return (f"{rec['classes_clean']} of {rec['total_classes']} check classes fully clean; "
            f"findings: {sc['BLOCKER']} blocker, {sc['WARN']} warning, "
            f"{sc['INFO']} informational.")


def md_cell(text: object) -> str:
    """A value safe inside one Markdown table cell: a literal pipe would end
    the cell, a newline would end the row, and package text such as
    <details> would be rendered as markup."""
    return (str(text).replace("\\", "\\\\").replace("|", "\\|")
            .replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace("\r", "").replace("\n", "<br>"))


def md_class_table(rec: dict) -> list[str]:
    lines = ["| # | Result | Check class | Conditions | Findings |", "|---|---|---|---|---|"]
    for i, c in enumerate(rec["classes"], 1):
        msgs = "<br>".join(md_cell(m) for m in capped(c["findings"])) or "none"
        lines.append(f"| {i} | {c['result']} | {md_cell(c['check'])} | {c['conditions']} | {msgs} |")
    return lines


def md_condition_table(rec: dict) -> list[str]:
    lines = ["| # | Result | Check | Condition verified | Value pulled (observed) | Compared against |",
             "|---|---|---|---|---|---|"]
    for i, r in enumerate(rec["condition_detail"], 1):
        lines.append(f"| {i} | {r['result']} | {md_cell(r['check'])} | {md_cell(r['condition'])} "
                     f"| {md_cell(r['observed'])} | {md_cell(r['compares_to'])} |")
    return lines


def render_md(rec: dict) -> str:
    lines = [f"# Publication Validation Report (pub-check): {rec['title']}", ""]
    fields = [("Target", f"`{rec['target']}`"), ("Validation date", rec["date"]),
              ("Tool", rec["tool"]),
              ("Coverage", f"{rec['total_checks']} individual checks across "
                           f"{rec['total_classes']} check classes, all run"),
              ("Blockers", str(rec["blockers"]))]
    if rec["exit_code"] is not None:
        fields.append(("Gate exit code", str(rec["exit_code"])))
    lines += [f"**{k}:** {v}  " for k, v in fields]
    lines += ["", f"**Result: {verdict(rec)}** {result_line(rec)}", "",
              "## Check-by-Check Results", "",
              "Every check class the tool carries is listed, whether or not it raised a "
              "finding. Conditions is the number of individual verifications inside the class.",
              ""]
    lines += md_class_table(rec)
    lines += ["", "## All Individual Conditions: Observed vs Expected", "",
              f"Every one of the {rec['total_checks']} individual conditions, with the value "
              "the check pulled from this package and what it was compared against. NA rows "
              "state why the condition does not apply to this package.", ""]
    lines += md_condition_table(rec)
    return "\n".join(lines) + "\n"


CSS = """
:root{--ink:#0a2540;--accent:#2248e5;--muted:#6b7380;--alt:#f2f6fb;--border:#d5dae0;
--bad:#b42318;--badbg:#fdecea;--warn:#8a5a00;--warnbg:#fff4d6;--good:#15803d;--goodbg:#e8f5ec;
--na:#6b7380;--nabg:#f1f2f4;--bg:#fff}
@media (prefers-color-scheme:dark){:root{--ink:#e6ebf2;--accent:#8aa2ff;--muted:#9aa3ae;
--alt:#18212c;--border:#2c3643;--bad:#ff8a80;--badbg:#3a1714;--warn:#ffd27a;--warnbg:#3a2d0c;
--good:#6fd394;--goodbg:#10301d;--na:#9aa3ae;--nabg:#222a33;--bg:#0f151c}}
*{box-sizing:border-box}
body{margin:0;padding:24px 16px;background:var(--bg);color:var(--ink);
font:14px/1.45 Inter,"Helvetica Neue",Arial,sans-serif}
main{max-width:1400px;margin:0 auto;min-width:0}
h1{font-size:22px;margin:0 0 12px;overflow-wrap:anywhere}h2{font-size:17px;margin:28px 0 8px}
dl{display:grid;grid-template-columns:max-content minmax(0,1fr);gap:4px 16px;margin:0 0 12px}
dt{color:var(--muted)}dd{margin:0;overflow-wrap:anywhere}
.verdict{padding:10px 14px;border-radius:6px;font-weight:600;overflow-wrap:anywhere}
.verdict.ok{background:var(--goodbg);color:var(--good)}.verdict.no{background:var(--badbg);color:var(--bad)}
.wrap{overflow-x:auto;max-width:100%}
table{border-collapse:collapse;width:100%;font-size:13px}
th,td{border:1px solid var(--border);padding:5px 7px;text-align:left;vertical-align:top}
th,td.n,td.r,td code{white-space:nowrap}
td.t{overflow-wrap:anywhere;min-width:16ch}
th{background:var(--alt);position:sticky;top:0}
td.r{font-weight:600;white-space:nowrap}
td.PASS{color:var(--good);background:var(--goodbg)}td.BLOCKER{color:var(--bad);background:var(--badbg)}
td.WARN{color:var(--warn);background:var(--warnbg)}td.NA,td.INFO{color:var(--na);background:var(--nabg)}
code{font-family:"JetBrains Mono",Menlo,monospace;font-size:12px}
p.note{color:var(--muted)}
"""


def result_class(result: str) -> str:
    return result.split()[0] if result else ""


def render_html(rec: dict) -> str:
    e = html.escape
    out = ["<!DOCTYPE html>", '<html lang="en"><head><meta charset="utf-8">',
           '<meta name="viewport" content="width=device-width, initial-scale=1">',
           f"<title>pub-check Validation Report</title><style>{CSS}</style></head><body><main>",
           f"<h1>Publication Validation Report (pub-check): {e(rec['title'])}</h1><dl>"]
    fields = [("Target", f"<code>{e(rec['target'])}</code>"), ("Validation date", e(rec["date"])),
              ("Tool", e(rec["tool"])),
              ("Coverage", f"{rec['total_checks']} individual checks across "
                           f"{rec['total_classes']} check classes, all run"),
              ("Blockers", str(rec["blockers"]))]
    if rec["exit_code"] is not None:
        fields.append(("Gate exit code", str(rec["exit_code"])))
    out += [f"<dt>{k}</dt><dd>{v}</dd>" for k, v in fields]
    out += ["</dl>",
            f'<p class="verdict {"ok" if rec["publication_ready"] else "no"}">'
            f"{e(verdict(rec))} {e(result_line(rec))}</p>",
            "<h2>Check-by-Check Results</h2>",
            '<p class="note">Every check class the tool carries is listed, whether or not it '
            "raised a finding. Conditions is the number of individual verifications inside "
            "the class.</p>",
            '<div class="wrap"><table><thead><tr><th>#</th><th>Result</th><th>Check class</th>'
            "<th>Cond.</th><th>Findings</th></tr></thead><tbody>"]
    for i, c in enumerate(rec["classes"], 1):
        msgs = "<br>".join(e(m) for m in capped(c["findings"])) or "none"
        out.append(f'<tr><td class="n">{i}</td><td class="r {result_class(c["result"])}">{e(c["result"])}'
                   f"</td><td><code>{e(c['check'])}</code></td><td class=\"n\">{c['conditions']}</td>"
                   f'<td class="t">{msgs}</td></tr>')
    out += ["</tbody></table></div>",
            "<h2>All Individual Conditions: Observed vs Expected</h2>",
            f'<p class="note">Every one of the {rec["total_checks"]} individual conditions, '
            "with the value the check pulled from this package and what it was compared "
            "against. NA rows state why the condition does not apply to this package.</p>",
            '<div class="wrap"><table><thead><tr><th>#</th><th>Result</th><th>Check</th>'
            "<th>Condition verified</th><th>Value pulled (observed)</th><th>Compared against</th>"
            "</tr></thead><tbody>"]
    for i, r in enumerate(rec["condition_detail"], 1):
        out.append(f'<tr><td class="n">{i}</td><td class="r {result_class(r["result"])}">{e(r["result"])}'
                   f"</td><td><code>{e(r['check'])}</code></td><td class=\"t\">{e(r['condition'])}</td>"
                   f'<td class="t">{e(r["observed"])}</td><td class="t">{e(r["compares_to"])}</td></tr>')
    out += ["</tbody></table></div></main></body></html>"]
    return "\n".join(out) + "\n"


def render_summary(rec: dict, report_files: str | None) -> str:
    """The step-summary section: verdict, class table, and the condition
    table collapsed. The condition table is left out, with a pointer to the
    report file, when it would push the summary past GitHub's size limit."""
    lines = [f"### Validation report: {rec['title']}", "",
             f"**{verdict(rec)}** {result_line(rec)} "
             f"{rec['total_checks']} individual checks across {rec['total_classes']} "
             "check classes, all run.", ""]
    if report_files:
        lines += [f"**Full report files:** {report_files}", ""]
    lines += md_class_table(rec)
    detail = ["", "<details>",
              f"<summary>All {rec['total_checks']} individual conditions: observed vs "
              "expected</summary>", ""] + md_condition_table(rec) + ["", "</details>"]
    text = "\n".join(lines + detail)
    if len(text.encode("utf-8")) > SUMMARY_LIMIT:
        where = report_files or "the validation report files"
        lines += ["", f"The condition table is too large for a step summary; it is in {where}."]
        text = "\n".join(lines)
    return text + "\n\n---\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("report_json", help="output of oasis_pub_check.py --json")
    ap.add_argument("--md", required=True, help="write the Markdown report here")
    ap.add_argument("--html", default=None, help="also write a self-contained HTML report here")
    ap.add_argument("--title", default="", help="report heading; defaults to the target")
    ap.add_argument("--exit-code", type=int, default=None,
                    help="the gate's own exit code, recorded in the report")
    ap.add_argument("--date", default=datetime.datetime.now(datetime.timezone.utc).date().isoformat())
    ap.add_argument("--step-summary", action="store_true",
                    help="append the report tables to $GITHUB_STEP_SUMMARY")
    ap.add_argument("--report-files", default=None,
                    help="with --step-summary: where the caller wrote the report files, "
                         "stated in the summary so a reader knows what to download")
    args = ap.parse_args()

    try:
        with open(args.report_json) as f:
            data = json.load(f)
        if not isinstance(data.get("conditions"), list) or not data["conditions"]:
            raise ValueError("no 'conditions' list")
        if not isinstance(data.get("findings"), list):
            raise ValueError("no 'findings' list")
    except (OSError, ValueError, AttributeError) as exc:
        print(f"validation_report: {args.report_json} is not a pub-check --json report: {exc}",
              file=sys.stderr)
        return 2

    rec = build_record(data, args.title, args.exit_code, args.date)
    with open(args.md, "w") as f:
        f.write(render_md(rec))
    if args.html:
        with open(args.html, "w") as f:
            f.write(render_html(rec))
    if args.step_summary:
        section = render_summary(rec, args.report_files)
        path = os.environ.get("GITHUB_STEP_SUMMARY")
        if path:
            with open(path, "a") as f:
                f.write(section + "\n")
        else:
            print(section)
    print(f"validation report: {rec['total_checks']} conditions across "
          f"{rec['total_classes']} classes -> {args.md}"
          + (f", {args.html}" if args.html else ""), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
