#!/usr/bin/env python3
# Copyright 2026 OASIS Open
# SPDX-License-Identifier: Apache-2.0
# Authored by Michael Coletta, Technical Advisor to OASIS Open.
"""Learn from every gate run: read what runs left behind, propose what to change.

Reads a directory tree of run records and prints what they say about the
gate itself, as candidates a person reviews (never as changes to the gate):

- Validation reports: `oasis_pub_check.py --json` output, or the Validation
  Report JSON (`condition_detail`). With --rerun, each report whose package
  is still on disk (`target_local_path`) is gated again with the current
  checker, and the two verdicts are compared: a finding the gate no longer
  raises, or one it newly raises.
- Publication audits (`findings` carrying a `classification`): defects a
  person found at intake. One that names no check class is a defect the gate
  passed, a candidate for a new check.
- Adjudications (--adjudications FILE, a JSON list of {"slug", "check",
  "verdict": "false-positive" | "real", "source"}): a finding TC
  Administration ruled a false positive is a candidate to narrow or split
  its check.

It also reports classes that fire on nearly every package (too broad, or a
systemic defect) and classes that never fire across the records (unexercised
or dead). --proposals DIR writes each candidate group as a draft proposal,
Status speculative, numbered after the highest NNN- file there.

Usage: harvest.py RECORDS_DIR... [--pub-check PATH] [--rerun] [--adjudications FILE]
                  [--proposals DIR] [--json OUT]
"""
import argparse
import collections
import datetime
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PUB_CHECK = os.path.join(HERE, "..", "pub-check", "oasis_pub_check.py")
RAISED = ("BLOCKER", "WARN")


def load_records(dirs):
    validations, audits = [], []
    for d in dirs:
        for root, _, files in os.walk(d):
            for name in sorted(files):
                if not name.endswith(".json"):
                    continue
                path = os.path.join(root, name)
                try:
                    data = json.load(open(path, encoding="utf-8"))
                except (OSError, ValueError):
                    continue
                if not isinstance(data, dict):
                    continue
                findings = data.get("findings")
                if "condition_detail" in data or (isinstance(findings, list) and findings
                                                  and isinstance(findings[0], dict) and "check" in findings[0]):
                    validations.append((path, data))
                elif isinstance(findings, list) and all(isinstance(x, dict) and "classification" in x
                                                        for x in findings):
                    audits.append((path, data))
    return validations, audits


def raised(report):
    """{(check, severity)} a report raised, from either JSON shape."""
    out = set()
    for c in report.get("condition_detail") or []:
        if c.get("result") in RAISED:
            out.add((c["check"], c["result"]))
    for x in report.get("findings") or []:
        if isinstance(x, dict) and x.get("severity") in RAISED and "check" in x:
            out.add((x["check"], x["severity"]))
    return out


def slug_of(path, report):
    return report.get("slug") or os.path.splitext(os.path.basename(path))[0]


def current_classes(pub_check):
    out = subprocess.run([sys.executable, pub_check, "--list-checks"], capture_output=True, text=True).stdout
    classes = {m.group(1): int(m.group(2)) for m in re.finditer(r"^\s+([a-z0-9-]+)\s+(\d+)$", out, re.M)}
    if not classes:
        sys.exit(f"harvest.py: no check classes from {pub_check} --list-checks")
    return classes


def rerun(pub_check, target):
    r = subprocess.run([sys.executable, pub_check, "--json", target], capture_output=True, text=True)
    try:
        return json.loads(r.stdout)
    except ValueError:
        return None


def harvest(dirs, pub_check=PUB_CHECK, do_rerun=False, adjudications=None):
    validations, audits = load_records(dirs)
    classes = current_classes(pub_check)
    per_class = collections.defaultdict(set)
    changed = []
    for path, rep in validations:
        slug = slug_of(path, rep)
        found = raised(rep)
        for check, _ in found:
            per_class[check].add(slug)
        target = rep.get("target_local_path")
        if do_rerun and target and os.path.isdir(target):
            now = rerun(pub_check, target)
            if now is not None:
                now_raised = raised(now)
                gone, new = sorted(found - now_raised), sorted(now_raised - found)
                if gone or new:
                    changed.append({"slug": slug, "report": path, "then": rep.get("total_checks"),
                                    "no_longer_raised": gone, "newly_raised": new})
    n = len({slug_of(p, r) for p, r in validations})
    broad = sorted((c, len(s)) for c, s in per_class.items() if n >= 4 and len(s) >= 0.75 * n)
    silent = sorted(c for c in classes if c not in per_class)
    false_pos = collections.defaultdict(list)
    for a in adjudications or []:
        if a.get("verdict") == "false-positive":
            false_pos[a["check"]].append(a)
    missed = []
    for path, aud in audits:
        for f in aud["findings"]:
            if f.get("classification") == "process":
                continue  # ballots, announcements, tickets: not in the package
            text = f"{f.get('title', '')} {f.get('body', '')}"
            if not any(re.search(rf"\b{re.escape(c)}\b", text) for c in classes):
                missed.append({"slug": aud.get("slug") or os.path.basename(path), "id": f.get("id"),
                               "classification": f.get("classification"), "severity": f.get("severity"),
                               "title": f.get("title"), "report": path})
    return {"validation_reports": len(validations), "packages": n, "audits": len(audits),
            "verdicts_changed": changed, "fires_almost_everywhere": broad,
            "never_fires": silent, "adjudicated_false_positives": dict(false_pos),
            "found_by_hand": missed}


def markdown(h):
    out = [f"# Gate harvest, {datetime.date.today().isoformat()}", "",
           f"{h['validation_reports']} validation reports over {h['packages']} packages, "
           f"{h['audits']} publication audits.", ""]
    out += ["## Verdicts the current gate would change", ""]
    for c in h["verdicts_changed"]:
        out.append(f"- **{c['slug']}** (report made with {c['then']} checks): "
                   f"no longer raised {c['no_longer_raised'] or 'none'}; newly raised {c['newly_raised'] or 'none'}")
    out += ["", "## Adjudicated false positives: narrow or split the check", ""]
    for check, items in sorted(h["adjudicated_false_positives"].items()):
        out.append(f"- **{check}**: {len(items)} ruled false positive ({', '.join(sorted({i['slug'] for i in items}))}); "
                   f"source: {items[0].get('source', '')}")
    out += ["", "## Found by hand at intake, no check names it: candidates for a new check", ""]
    for m in h["found_by_hand"]:
        out.append(f"- **{m['slug']} {m['id']}** ({m['classification']}, {m['severity']}): {m['title']}")
    out += ["", "## Fires on nearly every package: too broad, or a systemic defect", ""]
    out += [f"- **{c}**: {k} of {h['packages']} packages" for c, k in h["fires_almost_everywhere"]]
    out += ["", "## Never fires across these records: unexercised, or dead", ""]
    out += [f"- {c}" for c in h["never_fires"]]
    return "\n".join(out) + "\n"


def write_proposals(h, directory):
    nums = [int(m.group(1)) for f in os.listdir(directory) if (m := re.match(r"(\d{3})-", f))]
    n = max(nums, default=0)
    written = []
    groups = [(f"narrow-{check}", f"Narrow {check}: {len(items)} findings ruled false positives",
               "\n".join(f"- {i['slug']}: {i.get('source', '')}" for i in items))
              for check, items in sorted(h["adjudicated_false_positives"].items())]
    groups += [(f"new-check-{re.sub(r'[^a-z0-9]+', '-', (m['title'] or '').lower())[:40].strip('-')}",
                f"A check for: {m['title']}", f"- {m['slug']} {m['id']} ({m['classification']}, {m['severity']}): {m['report']}")
               for m in h["found_by_hand"]]
    for slug, title, evidence in groups:
        n += 1
        path = os.path.join(directory, f"{n:03d}-{slug}.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"# {n:03d}: {title}\nStatus: speculative\nRaised: {datetime.date.today().isoformat()}, "
                    f"harvest.py (proposal 013)\n\n## Problem\nThe run records say:\n{evidence}\n\n"
                    f"## Proposal\n(to write: attach the incident, then the check change)\n\n"
                    f"## How we will know it works\n\n## Risks\n\n## Review\n")
        written.append(path)
    return written


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dirs", nargs="+")
    ap.add_argument("--pub-check", default=PUB_CHECK)
    ap.add_argument("--rerun", action="store_true", help="gate each report's package again, where it is on disk")
    ap.add_argument("--adjudications")
    ap.add_argument("--proposals", help="write draft proposals into this directory")
    ap.add_argument("--json")
    a = ap.parse_args()
    adj = json.load(open(a.adjudications, encoding="utf-8")) if a.adjudications else []
    h = harvest(a.dirs, a.pub_check, a.rerun, adj)
    if a.json:
        json.dump(h, open(a.json, "w", encoding="utf-8"), indent=1, default=list)
    print(markdown(h))
    if a.proposals:
        for p in write_proposals(h, a.proposals):
            print("wrote", p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
