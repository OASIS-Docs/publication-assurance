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
  validation_report.py <report.json> --md <out.md> [--html <out.html>] [--pdf <out.pdf>]
                       [--title <label>] [--exit-code N] [--date YYYY-MM-DD]
                       [--step-summary [--report-files <text>]]

<report.json> is the output of `oasis_pub_check.py --json <target>`.
--step-summary also appends the class table, and the condition table in a
collapsed section, to $GITHUB_STEP_SUMMARY (stdout when that is unset).

--pdf prints the HTML report to an A4 landscape PDF with headless Chrome or
Chromium, driven over the DevTools pipe. No browser means no PDF and a
warning on stderr, never a different exit status.

Standard library only. Exit 0 on success, 2 when the input is not a pub-check
--json report.
"""
from __future__ import annotations

import argparse
import base64
import datetime
import html
import json
import os
import re
import select
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

try:
    import fcntl
except ImportError:      # Windows: the PDF step reports itself skipped
    fcntl = None

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
    if req in ("pdftotext", "pdffonts") and "pdf" not in {t.strip() for t in formats.split(",")}:
        return "NA: no PDF in the package, so there is nothing to read"
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
    detail = condition_rows(data)
    evaluated: dict[str, int] = {}
    na_reasons: dict[str, list[str]] = {}
    for r in detail:
        if r["result"] == "NA":
            if r["observed"] not in na_reasons.setdefault(r["check"], []):
                na_reasons[r["check"]].append(r["observed"])
        else:
            evaluated[r["check"]] = evaluated.get(r["check"], 0) + 1
    # A finding under a class with no registered conditions still gets a row.
    inventory = class_inventory(data["conditions"])
    known = {item["check"] for item in inventory}
    inventory += [{"check": k, "conditions": 0} for k in sorted(set(by_class) - known)]
    classes = []
    for item in inventory:
        name, total = item["check"], item["conditions"]
        fs = sorted(by_class.get(name, []), key=lambda f: SEV_ORDER.get(f["severity"], 9))
        done = evaluated.get(name, 0)
        # A finding outranks NA. A class none of whose conditions applied was
        # not checked: NA with the reason, not PASS. A partly evaluated class
        # says how much of it was.
        if fs:
            result = fs[0]["severity"]
        elif total and not done:
            result = "NA"
        else:
            result = "PASS"
        if result != "NA" and done < total:
            result += f" ({done} of {total} evaluated)"
        classes.append({"check": name, "conditions": total, "result": result,
                        "na_reasons": na_reasons.get(name, []) if result == "NA" else [],
                        "findings": [{"severity": f["severity"], "message": f["message"]}
                                     for f in fs]})
    sev = {s: sum(1 for f in data["findings"] if f["severity"] == s)
           for s in ("BLOCKER", "WARN", "INFO")}
    checked = [c for c in classes if c["result"] != "NA"]
    return {
        "title": title or data.get("target", "package"),
        "target": data.get("target", ""),
        "date": date, "tool": TOOL, "exit_code": exit_code,
        "total_checks": len(data["conditions"]), "total_classes": len(classes),
        "classes_evaluated": len(checked),
        "classes_not_evaluated": len(classes) - len(checked),
        "classes_clean": sum(1 for c in checked if not c["findings"]),
        "blockers": sev["BLOCKER"], "severity_counts": sev,
        "publication_ready": sev["BLOCKER"] == 0,
        "classes": classes, "condition_detail": detail,
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
    return (f"{rec['classes_clean']} of {rec['classes_evaluated']} evaluated check classes "
            f"fully clean; {rec['classes_not_evaluated']} not evaluated; findings: {sc['BLOCKER']} blocker, {sc['WARN']} warning, "
            f"{sc['INFO']} informational.")


MD_INLINE = "\\`*_[]~|"   # characters that open inline Markdown or end a table cell


def md_escape(text: object) -> str:
    """Package- or caller-supplied text shown literally in GitHub Markdown:
    emphasis, code, link and strikethrough markers are backslash-escaped,
    and HTML such as <img onerror=...> becomes entities, not markup.
    GitHub also turns text into math ($...$), mentions and issue links (@,
    #) and links (http://, www., name@host), none of which a backslash
    stops (checked against GitHub's own renderer): $, @ and # each go in a
    <span>, and the ':' of '://' and the '.' of 'www.' are escaped."""
    s = "".join("\\" + ch if ch in MD_INLINE else ch for ch in str(text))
    s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    s = re.sub(r":(?=//)", r"\\:", s)
    s = re.sub(r"(?i)\b(www)\.", r"\1\\.", s)
    return re.sub(r"[$@#]", lambda m: f"<span>{m.group()}</span>", s)


def md_text(text: object) -> str:
    """md_escape on one line, for a heading or a sentence."""
    return " ".join(md_escape(text).split())


def md_code(text: object) -> str:
    """Text as a Markdown code span, with a backtick fence longer than any
    backtick run inside it, so the text cannot close the span."""
    s = " ".join(str(text).split())
    run = max((len(m) for m in re.findall(r"`+", s)), default=0)
    fence = "`" * (run + 1)
    return f"{fence} {s} {fence}"


def md_cell(text: object) -> str:
    """A value safe inside one Markdown table cell: a literal pipe would end
    the cell, a newline would end the row, and package text such as
    <details> would be rendered as markup."""
    return md_escape(text).replace("\r", "").replace("\n", "<br>")


def class_notes(c: dict) -> list[str]:
    """The Findings cell of the class table: the findings, or for a class
    that was not evaluated, why."""
    return capped(c["findings"]) or c["na_reasons"]


def md_class_table(rec: dict) -> list[str]:
    lines = ["| # | Result | Check class | Conditions | Findings |", "|---|---|---|---|---|"]
    for i, c in enumerate(rec["classes"], 1):
        msgs = "<br>".join(md_cell(m) for m in class_notes(c)) or "none"
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
    lines = [f"# Publication Validation Report (pub-check): {md_text(rec['title'])}", ""]
    fields = [("Target", md_code(rec["target"])), ("Validation date", rec["date"]),
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
@media screen and (prefers-color-scheme:dark){:root{--ink:#e6ebf2;--accent:#8aa2ff;--muted:#9aa3ae;
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
td.t{overflow-wrap:anywhere;min-width:12em}
td.t.f{min-width:18em}
th{background:var(--alt);position:sticky;top:0}
td.r{font-weight:600;white-space:nowrap}
td.PASS{color:var(--good);background:var(--goodbg)}td.BLOCKER{color:var(--bad);background:var(--badbg)}
td.WARN{color:var(--warn);background:var(--warnbg)}td.NA,td.INFO{color:var(--na);background:var(--nabg)}
code{font-family:"JetBrains Mono",Menlo,monospace;font-size:12px}
p.note{color:var(--muted)}
a{color:var(--accent)}
@page{size:A4 landscape;margin:1.27cm}
@media print{
:root{--ink:#0a2540;--accent:#2248e5;--muted:#6b7380;--alt:#f2f6fb;--border:#d5dae0;
--bad:#b42318;--badbg:#fdecea;--warn:#8a5a00;--warnbg:#fff4d6;--good:#15803d;--goodbg:#e8f5ec;
--na:#6b7380;--nabg:#f1f2f4;--bg:#fff}
*{-webkit-print-color-adjust:exact;print-color-adjust:exact}
body{padding:0;font-size:9pt}
main{max-width:none}
h1{font-size:15pt}h2{font-size:12pt;margin:16pt 0 6pt;break-after:avoid}
p.note{break-after:avoid}
.wrap{overflow:visible}
table{font-size:8pt;line-height:1.3}
th,td{padding:2.5pt 4pt}
th{position:static;background:var(--ink);color:#fff}
thead{display:table-header-group}
tr{break-inside:avoid}
td.t{min-width:9em}td.t.f{min-width:14em}
code{font-size:7.5pt}
}
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
        msgs = "<br>".join(e(m) for m in class_notes(c)) or "none"
        out.append(f'<tr><td class="n">{i}</td><td class="r {result_class(c["result"])}">{e(c["result"])}'
                   f"</td><td><code>{e(c['check'])}</code></td><td class=\"n\">{c['conditions']}</td>"
                   f'<td class="t f">{msgs}</td></tr>')
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
                   f'<td class="t f">{e(r["observed"])}</td><td class="t">{e(r["compares_to"])}</td></tr>')
    out += ["</tbody></table></div></main></body></html>"]
    return "\n".join(out) + "\n"


def render_summary(rec: dict, report_files: str | None) -> str:
    """The step-summary section: verdict, class table, and the condition
    table collapsed. The condition table is left out, with a pointer to the
    report file, when it would push the summary past GitHub's size limit."""
    lines = [f"### Validation report: {md_text(rec['title'])}", "",
             f"**{verdict(rec)}** {result_line(rec)} "
             f"{rec['total_checks']} individual checks across {rec['total_classes']} "
             "check classes, all run.", ""]
    if report_files:
        lines += [f"**Full report files:** {md_text(report_files)}", ""]
    lines += md_class_table(rec)
    detail = ["", "<details>",
              f"<summary>All {rec['total_checks']} individual conditions: observed vs "
              "expected</summary>", ""] + md_condition_table(rec) + ["", "</details>"]
    text = "\n".join(lines + detail)
    if len(text.encode("utf-8")) > SUMMARY_LIMIT:
        where = md_text(report_files) if report_files else "the validation report files"
        lines += ["", f"The condition table is too large for a step summary; it is in {where}."]
        text = "\n".join(lines)
    return text + "\n\n---\n"


BROWSERS = ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome",
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Chromium.app/Contents/MacOS/Chromium")
PDF_TIMEOUT = 120  # seconds for the whole browser session; $PUBCHECK_PDF_TIMEOUT overrides


def find_browser() -> str | None:
    """A headless-capable Chrome or Chromium: $PUBCHECK_CHROME alone when it
    is set, else the first of BROWSERS on PATH or at its absolute path.
    GitHub's ubuntu-latest runners carry google-chrome."""
    chosen = os.environ.get("PUBCHECK_CHROME")
    for name in ((chosen,) if chosen else BROWSERS):
        path = shutil.which(name) or (name if os.path.isabs(name) and os.access(name, os.X_OK)
                                      else None)
        if path:
            return path
    return None


def footer_template(rec: dict) -> str:
    """Chrome's print footer: the report title and date on the left, Page X
    of Y on the right. Chrome fills the pageNumber and totalPages spans."""
    e = html.escape
    return ('<div style="width:100%;margin:0 1.27cm;padding-top:3px;border-top:1px solid #d5dae0;'
            'font:7.5pt Inter,\'Helvetica Neue\',Arial,sans-serif;color:#6b7380;display:flex;'
            'justify-content:space-between;-webkit-print-color-adjust:exact">'
            f'<span>pub-check Validation Report: {e(rec["title"])} | {e(rec["date"])}</span>'
            '<span>Page <span class="pageNumber"></span> of <span class="totalPages"></span>'
            '</span></div>')


class _DevTools:
    """The Chrome DevTools protocol over --remote-debugging-pipe: the browser
    reads NUL-terminated JSON commands on fd 3 and writes replies and events
    on fd 4. A pipe needs no websocket, so this stays standard library."""

    def __init__(self, browser: str, profile: str):
        to_chrome, self._w = os.pipe()
        self._r, from_chrome = os.pipe()

        def wire():
            # Move both ends clear of 3 and 4 first, so neither dup2 can
            # overwrite the other; dup2 leaves the results inheritable.
            a = fcntl.fcntl(to_chrome, fcntl.F_DUPFD, 10)
            b = fcntl.fcntl(from_chrome, fcntl.F_DUPFD, 10)
            os.dup2(a, 3)
            os.dup2(b, 4)

        args = [browser, "--headless=new", "--remote-debugging-pipe", "--disable-gpu",
                "--no-first-run", "--no-default-browser-check", "--disable-extensions",
                f"--user-data-dir={profile}"]
        if sys.platform.startswith("linux"):
            # Ubuntu 24.04 blocks the unprivileged user namespaces Chrome's
            # sandbox needs. The page is our own escaped HTML with no script.
            args.append("--no-sandbox")
        # Its own session, so close() can end every helper process the
        # browser started, not only the one it launched.
        self.proc = subprocess.Popen(args, preexec_fn=wire, close_fds=False,
                                     start_new_session=True, stdin=subprocess.DEVNULL,
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        os.close(to_chrome)
        os.close(from_chrome)
        self._buf, self._next, self._events = b"", 0, []
        self.timeout = float(os.environ.get("PUBCHECK_PDF_TIMEOUT") or PDF_TIMEOUT)
        self.deadline = time.monotonic() + self.timeout

    def _read(self) -> dict:
        while b"\0" not in self._buf:
            left = self.deadline - time.monotonic()
            if left <= 0 or not select.select([self._r], [], [], left)[0]:
                raise TimeoutError(f"no reply from the browser within {self.timeout:g}s")
            chunk = os.read(self._r, 1 << 20)
            if not chunk:
                raise RuntimeError("the browser closed the DevTools pipe")
            self._buf += chunk
        msg, self._buf = self._buf.split(b"\0", 1)
        return json.loads(msg)

    def call(self, method: str, session: str | None = None, **params) -> dict:
        self._next += 1
        msg = {"id": self._next, "method": method, "params": params}
        if session:
            msg["sessionId"] = session
        os.write(self._w, json.dumps(msg).encode() + b"\0")
        while True:
            reply = self._read()
            if reply.get("id") == self._next:
                if "error" in reply:
                    raise RuntimeError(f"{method}: {reply['error'].get('message')}")
                return reply.get("result", {})
            self._events.append(reply)

    def wait_event(self, method: str, session: str) -> None:
        while True:
            for ev in self._events:
                if ev.get("method") == method and ev.get("sessionId") == session:
                    self._events.remove(ev)
                    return
            self._events.append(self._read())

    def close(self) -> None:
        try:
            self.call("Browser.close")
        except (OSError, RuntimeError, TimeoutError):
            pass
        for fd in (self._w, self._r):
            os.close(fd)
        try:
            self.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.proc.wait()
        try:
            os.killpg(self.proc.pid, signal.SIGKILL)   # stragglers in its session
        except (ProcessLookupError, PermissionError):
            pass


def render_pdf(rec: dict, html_path: str, pdf_path: str) -> str | None:
    """Print the HTML report to an A4 landscape PDF with headless Chrome:
    light theme whatever the system scheme, 1.27cm margins, header rows
    repeated on every page, result colours kept, and a footer carrying the
    title and Page X of Y. Returns None on success, else why no PDF was
    written; a missing browser is a reason, never an exception."""
    browser = find_browser()
    if not browser:
        return "no Chrome or Chromium found (set PUBCHECK_CHROME to one)"
    if fcntl is None:
        return "PDF printing needs a POSIX host (the DevTools pipe uses fds 3 and 4)"
    with tempfile.TemporaryDirectory(prefix="pubcheck-chrome-") as profile:
        try:
            dt = _DevTools(browser, profile)
        except OSError as exc:
            return f"could not start {browser}: {exc}"
        try:
            target = dt.call("Target.createTarget", url="about:blank")["targetId"]
            session = dt.call("Target.attachToTarget", targetId=target, flatten=True)["sessionId"]
            dt.call("Page.enable", session)
            dt.call("Emulation.setEmulatedMedia", session, media="print",
                    features=[{"name": "prefers-color-scheme", "value": "light"}])
            dt.call("Page.navigate", session, url=Path(html_path).resolve().as_uri())
            dt.wait_event("Page.loadEventFired", session)
            margin = 0.5  # inches: 1.27cm
            pdf = dt.call("Page.printToPDF", session, landscape=True,
                          paperWidth=11.69, paperHeight=8.27, marginTop=margin,
                          marginBottom=margin, marginLeft=margin, marginRight=margin,
                          printBackground=True, preferCSSPageSize=True,
                          displayHeaderFooter=True, headerTemplate="<span></span>",
                          footerTemplate=footer_template(rec))
        except (OSError, RuntimeError, TimeoutError, KeyError, ValueError) as exc:
            return f"{browser} could not print the report: {exc}"
        finally:
            dt.close()
    data = base64.b64decode(pdf["data"])
    if not data.startswith(b"%PDF-"):
        return f"{browser} returned something that is not a PDF"
    with open(pdf_path, "wb") as f:
        f.write(data)
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("report_json", help="output of oasis_pub_check.py --json")
    ap.add_argument("--md", required=True, help="write the Markdown report here")
    ap.add_argument("--html", default=None, help="also write a self-contained HTML report here")
    ap.add_argument("--pdf", default=None,
                    help="also print the HTML report to an A4 landscape PDF here with headless "
                         "Chrome; skipped with a warning (exit status unchanged) when no "
                         "browser is available")
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
    pdf_written = False
    if args.pdf:
        with tempfile.TemporaryDirectory(prefix="pubcheck-report-") as tmp:
            page = args.html or os.path.join(tmp, "pubcheck-validation.html")
            if not args.html:
                with open(page, "w") as f:
                    f.write(render_html(rec))
            why = render_pdf(rec, page, args.pdf)
        if why:
            print(f"validation_report: warning: PDF not written: {why}", file=sys.stderr)
        else:
            pdf_written = True
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
          + (f", {args.html}" if args.html else "")
          + (f", {args.pdf}" if pdf_written else ""), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
