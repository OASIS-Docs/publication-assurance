<!--
Copyright 2026 OASIS Open
SPDX-License-Identifier: Apache-2.0
Authored by Michael Coletta, Technical Advisor to OASIS Open.
-->

# harvest: learn from every publication-checks run

Every run of the publication checks leaves records. `harvest.py` reads them and says what
they mean for the checks themselves, so no run's output is wasted:

| It reads | It proposes |
|---|---|
| Validation reports (`oasis_pub_check.py --json`, or the Validation Report JSON), and with `--rerun` the current checks' verdict on each package still on disk | Findings the current checks no longer raise (confirm each was a false positive or a fixed package) and findings they newly raise (triage each: a real defect, or a new false positive) |
| Adjudications (`--adjudications`, a JSON list of `{"slug", "check", "verdict", "source"}`) | Checks to narrow or split, where TC Administration ruled a finding a false positive |
| Publication audits (`findings` with a `classification`) | Defects found by hand at intake that no check names: candidates for a new check (process findings, about ballots or announcements, are left out) |
| All of them | Check classes that fire on nearly every package (too broad, or a systemic defect) and classes that never fire (unexercised, or dead) |

```bash
python3 harvest/harvest.py RECORDS_DIR... [--rerun] [--adjudications FILE] \
        [--proposals DIR] [--json OUT] [--pub-check PATH]
```

It changes nothing in the publication checks. `--proposals DIR` writes each candidate
group as a draft proposal, `Status: speculative`, numbered after the highest
`NNN-` file in `DIR`, for a person to attach the incident to and review.

Its first run, over TC Administration's records of August and September 2026
(26 validation reports, 20 packages, 9 audits), found:
- the OData v4.02 csd02 `template` and `filenames` blockers, ruled false
  positives in August, still raised by the current checks (now fixed:
  `tests/test_odata_adjudications.py`);
- the `package-refs` directory false positive gone since v1.6;
- 29 classes that no recorded run had ever exercised.
