"""advance_stage.py cuts the next stage of an OASIS Markdown spec.

DMLex v1.1 WD01 (Sep 2026) was cut from the v1.0 OS Markdown edition by a
hand-written script asserting eleven replacements
(~/h/lexidma-helpers/make_wd01.py). This tool does the same job for any spec
in the OASIS Markdown template, and refuses rather than guess.

Fixtures, both real:

- dmlex-v1.0-os.md: the DMLex v1.0 OS Markdown edition from
  MColetta-OASIS/lexidma branch markdown-conversion at commit 83827ff.
  It keeps lines 1 to 116 (the front matter, the citation and the Notices),
  9706 to 9719 (Appendix C's schema links) and 9925 to 9950 (the change log,
  whose older draft URLs must not move).
- expected-dmlex-v1.1-wd01.md: make_wd01.py's own replacements applied to
  the same excerpt, with two adjustments. Its two `.pdf.pdf]` typo fixes are
  left out, because they are content edits rather than stage edits. The
  Notices year moves to 2026, which the hand script missed and the gate's
  date-sync check reports.
- niem-pubs-v1.0-pn01-front.md: the first 40 lines of the NIEMOpen Project
  Note (OASIS-Docs/niemopen 5630ee4), a front matter shape the tool refuses.
"""

from __future__ import annotations

import importlib.util
import subprocess
from datetime import date

import pytest

from conftest import FIXTURES, REPO_ROOT, oasis_pub_check

FIX = FIXTURES / "advance_stage"
TOOL = REPO_ROOT / "pub-check/advance_stage.py"


def load():
    spec = importlib.util.spec_from_file_location("advance_stage", TOOL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def dmlex():
    return (FIX / "dmlex-v1.0-os.md").read_text(encoding="utf-8")


def cut(text=None, mod=None, **kw):
    mod = mod or load()
    kw.setdefault("when", date(2026, 9, 24))
    return mod.StageAdvance(text or dmlex()).advance(**kw)


def refused(**kw):
    mod = load()
    with pytest.raises(mod.Refused) as e:
        cut(mod=mod, **kw)
    return str(e.value)


WD01 = dict(to="wd01", version="1.1", previous="source", formats=["md", "html", "pdf"],
            unpublished_ok=True)


def test_dmlex_wd01_matches_the_hand_cut_edition():
    assert cut(**WD01) == (FIX / "expected-dmlex-v1.1-wd01.md").read_text(encoding="utf-8")


def test_it_regenerates_the_citation_and_so_drops_the_doubled_oasis():
    out = cut(**WD01)
    assert "OASIS OASIS Standard" not in out and "OASIS Working Draft 01." in out


def test_older_draft_urls_in_the_change_log_do_not_move():
    out = cut(**WD01)
    for old in ("v1.0/csd04/dmlex-v1.0-csd04.pdf.pdf", "v1.0/csd03/dmlex-v1.0-csd03.pdf.pdf",
                "v1.0/csd02/dmlex-v1.0-csd02.pdf"):
        assert old in out, old


def test_a_published_stage_cut_passes_the_gate_front_matter_checks(tmp_path, monkeypatch):
    out = cut(to="csd01", version="1.1", previous="source")
    stage = tmp_path / "lexidma/dmlex/v1.1/csd01"
    stage.mkdir(parents=True)
    (stage / "dmlex-v1.1-csd01.md").write_text(out, encoding="utf-8")
    monkeypatch.setenv("PUB_CHECK_OFFLINE", "1")
    f = oasis_pub_check.Findings()
    oasis_pub_check.run(str(stage), f)
    watched = {"stage-name", "version-naming", "date-sync", "stage-token", "title-version"}
    bad = [x for x in f.items if x["check"] in watched and x["severity"] != "INFO"]
    assert bad == [], bad
    assert "OASIS Committee Specification Draft 01." in out
    assert "https://docs.oasis-open.org/lexidma/dmlex/v1.1/csd01/dmlex-v1.1-csd01.pdf (Authoritative)" in out


def test_a_working_draft_needs_unpublished_ok():
    assert "--unpublished-ok" in refused(**{**WD01, "unpublished_ok": False})


def test_a_new_version_needs_an_explicit_previous_stage():
    assert "--previous" in refused(to="csd01", version="1.1")


@pytest.mark.parametrize("to", ["csprd01", "cos01", "os01", "csd", "cs", "zz01"])
def test_retired_unknown_and_misnumbered_stages_are_refused(to):
    refused(to=to, version="1.1", previous="source")


def test_an_os_version_takes_no_further_stage():
    assert "final stage" in refused(to="cs02")


def test_a_track_change_is_refused():
    assert "track" in refused(to="cnd01", version="1.1", previous="source")


def test_a_niem_project_note_is_refused():
    mod = load()
    with pytest.raises(mod.Refused, match="shape"):
        mod.StageAdvance((FIX / "niem-pubs-v1.0-pn01-front.md").read_text(encoding="utf-8"))


def test_an_unknown_citation_shape_is_refused():
    text = dmlex().replace("Edited by David Filip", "Ed. David Filip", 1)
    assert "citation" in refused(text=text, **WD01)


def test_a_missing_site_is_refused():
    text = dmlex().replace("Copyright © OASIS Open 2025.", "Copyright OASIS 2025.", 1)
    assert "Notices" in refused(text=text, **WD01)


def test_the_shared_stage_vocabulary_is_the_gates():
    mod = load()
    assert mod.VALID_STAGE_PREFIXES is oasis_pub_check.VALID_STAGE_PREFIXES or \
        mod.VALID_STAGE_PREFIXES == oasis_pub_check.VALID_STAGE_PREFIXES
    assert set(mod.RETIRED_STAGE_TOKENS) == {"csprd", "cnprd", "cos", "csdpr", "cndpr"}


def _git_source(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    src = repo / "dmlex-v1.0-os.md"
    src.write_text(dmlex(), encoding="utf-8")
    g = ["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@example.org"]
    subprocess.run(g[:3] + ["init", "-q"], check=True)
    subprocess.run(g + ["add", "."], check=True)
    subprocess.run(g + ["commit", "-qm", "source"], check=True)
    return repo, src


ARGS = ["--to", "wd01", "--version", "1.1", "--previous", "source", "--formats",
        "md,html,pdf", "--unpublished-ok", "--date", "2026-09-24"]


def test_the_cli_dry_runs_by_default_and_writes_only_on_request(tmp_path, capsys):
    repo, src = _git_source(tmp_path)
    assert load().main([str(src), *ARGS]) == 0
    assert not (repo / "dmlex-v1.1-wd01.md").exists()
    assert "dry run" in capsys.readouterr().out
    assert load().main([str(src), *ARGS, "--write"]) == 0
    assert (repo / "dmlex-v1.1-wd01.md").read_text(encoding="utf-8") == \
        (FIX / "expected-dmlex-v1.1-wd01.md").read_text(encoding="utf-8")
    assert load().main([str(src), *ARGS, "--write"]) == 1   # never overwrites


def test_a_dirty_source_is_refused(tmp_path):
    repo, src = _git_source(tmp_path)
    src.write_text(dmlex() + "\nedit\n", encoding="utf-8")
    assert load().main([str(src), *ARGS]) == 1
    assert load().main([str(src), *ARGS, "--allow-dirty"]) == 0


def test_the_date_is_required():
    with pytest.raises(SystemExit):
        load().main([str(FIX / "dmlex-v1.0-os.md"), "--to", "csd01"])


# Counterexamples from the independent verification of this change.

CSAF = REPO_ROOT / "examples/csaf/v2.0"


def test_the_previous_stage_keeps_the_authoritative_md_line():
    """CSAF v2.0 cs02's own Previous stage lists cs01's .md (Authoritative) first."""
    src = (CSAF / "cs01/csaf-v2.0-cs01.md").read_text(encoding="utf-8")
    out = cut(text=src, to="cs02", previous="source")
    prev = out.split("#### Previous stage:")[1].split("####")[0]
    assert "https://docs.oasis-open.org/csaf/csaf/v2.0/cs01/csaf-v2.0-cs01.md (Authoritative)" in prev


def test_the_cut_matches_the_published_csaf_cs02_front_matter():
    src = (CSAF / "cs01/csaf-v2.0-cs01.md").read_text(encoding="utf-8")
    real = (CSAF / "cs02/csaf-v2.0-cs02.md").read_text(encoding="utf-8")
    out = cut(text=src, to="cs02", previous="source")
    for heading in ("This stage:", "Previous stage:", "Latest stage:"):
        block = lambda t: t.split(f"#### {heading}")[1].split("####")[0].strip()
        assert block(out) == block(real), heading


@pytest.mark.parametrize("src_stage,to", [("cs01", "csd01"), ("cs02", "csd01"), ("csd01", "os")])
def test_a_stage_that_exists_or_skips_cs_is_refused(src_stage, to):
    src = dmlex().replace("/v1.0/os/", f"/v1.0/{src_stage}/").replace(
        "dmlex-v1.0-os.", f"dmlex-v1.0-{src_stage}.").replace(
        "## OASIS Standard\n", "## " + load().stage_label(src_stage) + "\n", 1)
    refused(text=src, to=to, previous="source")


def test_a_draft_after_a_cs_with_a_higher_number_is_allowed():
    src = (CSAF / "cs01/csaf-v2.0-cs01.md").read_text(encoding="utf-8")
    assert "Committee Specification Draft 02" in cut(text=src, to="csd02", previous="source")


def test_headings_without_a_blank_line_and_a_wrapped_citation_are_read():
    src = dmlex().replace("#### This stage:\n\n", "#### This stage:\n", 1)
    src = src.replace(" Edited by David Filip,", "\nEdited by David Filip,", 1)
    out = cut(text=src, **WD01)
    assert "OASIS Working Draft 01. <https://docs.oasis-open.org/lexidma/dmlex/v1.1/wd01/" in out


@pytest.mark.parametrize("ver", ["0.9", "1.0", "2", "1.1.1"])
def test_a_version_that_does_not_move_forward_is_refused(ver):
    refused(to="csd01", version=ver, previous="source")


def test_http_self_urls_and_derived_file_names_move_with_the_stage():
    src = (CSAF / "cs01/csaf-v2.0-cs01.md").read_text(encoding="utf-8")
    src += ("\nSee http://docs.oasis-open.org/csaf/csaf/v2.0/cs01/schemas/x.json and "
            "https://docs.oasis-open.org/csaf/csaf/v2.0/cs01/csaf-v2.0-cs01-DIFF.pdf\n")
    out = cut(text=src, to="cs02", previous="source")
    tail = out.rsplit("\nSee ", 1)[1]
    assert "v2.0/cs02/schemas/x.json" in tail and "v2.0/cs02/csaf-v2.0-cs02-DIFF.pdf" in tail, tail


def test_angle_bracketed_latest_urls_keep_their_brackets():
    src = dmlex().replace(
        "https://docs.oasis-open.org/lexidma/dmlex/v1.0/dmlex-v1.0.html \\\n"
        "https://docs.oasis-open.org/lexidma/dmlex/v1.0/dmlex-v1.0.pdf (Authoritative)",
        "<https://docs.oasis-open.org/lexidma/dmlex/v1.0/dmlex-v1.0.html> \\\n"
        "<https://docs.oasis-open.org/lexidma/dmlex/v1.0/dmlex-v1.0.pdf> (Authoritative)", 1)
    out = cut(text=src, **WD01)
    latest = out.split("#### Latest stage:")[1].split("####")[0]
    assert "<https://docs.oasis-open.org/lexidma/dmlex/v1.1/dmlex-v1.1.pdf> (Authoritative)" in latest, latest


def test_crlf_and_a_copyright_range_are_handled():
    src = dmlex().replace("Copyright © OASIS Open 2025.", "Copyright © OASIS Open 2023-2025.")
    out = cut(text=src.replace("\n", "\r\n"), **WD01)
    assert "\r\n" in out and "Copyright © OASIS Open 2023-2026." in out


# Second verification round. The OData fixture keeps lines 1 to 99, 264 to 284
# and 2282 to 2288 of odata-data-aggregation-ext-v4.0-cs04.md
# (OASIS-Docs/odata 93700ed): the front matter, a command line naming the
# source's own file, and a vocabulary URL wrapped across two lines.

ODATA = FIX / "odata-data-aggregation-ext-v4.0-cs04.md"


def test_stale_stage_references_are_refused_with_their_lines():
    msg = refused(text=ODATA.read_text(encoding="utf-8"), to="csd05", previous="source")
    assert "stale" in msg
    assert "odata-data-aggregation-ext-v4.0-cs04.html" in msg      # the bare file name
    assert "v4.0/cs04/vocabularies" in msg                         # the wrapped URL


def test_leave_stale_writes_the_cut_and_reports_them():
    mod = load()
    adv = mod.StageAdvance(ODATA.read_text(encoding="utf-8"))
    out = adv.advance(to="csd05", when=date(2026, 9, 24), previous="source", leave_stale=True)
    assert "## Committee Specification Draft 05" in out
    assert len(adv.stale) >= 3, adv.stale


def test_a_draft_number_already_cited_as_previous_is_refused():
    src = (CSAF / "cs01/csaf-v2.0-cs01.md").read_text(encoding="utf-8")
    prev = src.split("#### Previous stage:")[1].split("####")[0]
    src = src.replace(prev, prev.replace("/csd01/", "/csd03/").replace("-csd01.", "-csd03."), 1)
    assert "csd03" in src.split("#### Previous stage:")[1].split("####")[0]
    refused(text=src, to="csd02", previous="source")


def test_dmlex_has_no_stale_reference():
    mod = load()
    adv = mod.StageAdvance(dmlex())
    adv.advance(when=date(2026, 9, 24), **WD01)
    assert adv.stale == []
