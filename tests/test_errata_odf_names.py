# Copyright 2026 OASIS Open
# SPDX-License-Identifier: Apache-2.0
# Authored by Michael Coletta, Technical Advisor to OASIS Open.
"""Errata Latest-stage names and ODF's mixed-case names (ledger T-20261030-07).

The ODF v1.4 Errata 01 csd01 package (TCADMIN-4807) drew six blockers that
the document did not deserve:

- stage-token: its Latest-stage URLs, .../v1.4/errata01/OpenDocument-v1.4-
  errata01.{odt,html,pdf}, were read as embedding a stage token. errataNN
  there is the Errata Work Product's own name, in its own required /errataNN/
  directory (Naming Directives v1.7 Section 4), as OData published it:
  odata/odata/v4.0/errata03/odata-v4.0-errata03.html.
- case: OpenDocument-v1.4-errata01-csd01.{odt,html,pdf} were refused as
  mixed case. The Naming Directives let TCs use mixed case and camel case;
  ODF's WP-abbrev and directory have been 'OpenDocument' since v1.2.

Each allowance is narrow, and the negatives below must still be refused.
Fixture names and URLs are copied from the staged ODF package.
"""

from __future__ import annotations

from conftest import oasis_pub_check as pc

BASE = "https://docs.oasis-open.org/office/OpenDocument/v1.4/errata01"
ODF_NAMES = [f"OpenDocument-v1.4-errata01-csd01.{e}" for e in ("odt", "html", "pdf")]


def _cover(latest: list[str], this_dir: str = f"{BASE}/csd01") -> str:
    this = " ".join(f'<a href="{this_dir}/OpenDocument-v1.4-errata01-csd01.{e}">'
                    f"{this_dir}/OpenDocument-v1.4-errata01-csd01.{e}</a>"
                    for e in ("odt", "html", "pdf"))
    lat = " ".join(f'<a href="{u}">{u}</a>' for u in latest)
    return (f"<html><body><p>This stage:</p><p>{this}</p><p>Previous stage:</p><p>N/A</p>"
            f"<p>Latest stage:</p><p>{lat}</p>"
            f"<p>Technical Committee:</p><p>OASIS ODF TC</p></body></html>")


def _stage_token(latest, errata_dir="errata01"):
    f = pc.Findings()
    pc.check_stage_token("", _cover(latest), "csd01", f, errata_dir=errata_dir,
                         wp_dir="OpenDocument", version="v1.4")
    return [i for i in f.items if i["check"] == "stage-token" and i["severity"] == "BLOCKER"]


ODF_LATEST = [f"{BASE}/OpenDocument-v1.4-errata01.{e}" for e in ("odt", "html", "pdf")]


def test_odf_errata_latest_stage_passes():
    assert _stage_token(ODF_LATEST) == []


def test_errata_latest_with_a_second_stage_token_still_blocks():
    out = _stage_token([f"{BASE}/OpenDocument-v1.4-errata01-csd01.html"])
    assert len(out) == 1, out


def test_another_errata_number_still_blocks():
    out = _stage_token([f"{BASE.replace('errata01', 'errata02')}/OpenDocument-v1.4-errata02.html"])
    assert len(out) == 1, out


def test_errata_token_outside_an_errata_package_still_blocks():
    assert len(_stage_token(ODF_LATEST, errata_dir="")) == 3


def test_errata_token_outside_its_own_directory_still_blocks():
    out = _stage_token(["https://docs.oasis-open.org/office/OpenDocument/v1.4/"
                        "OpenDocument-v1.4-errata01.html"])
    assert len(out) == 1, out


def test_csd_token_in_errata_latest_still_blocks():
    out = _stage_token([f"{BASE}/OpenDocument-v1.4-csd01.html"])
    assert len(out) == 1, out


def test_errata_latest_complete_variant_passes():
    assert _stage_token([f"{BASE}/OpenDocument-v1.4-errata01-complete.html"]) == []


# Counterexamples from the independent review: each passed the first draft.
def test_errata_latest_for_another_version_still_blocks():
    out = _stage_token(["https://docs.oasis-open.org/office/OpenDocument/v1.3/errata01/"
                        "OpenDocument-v1.3-errata01.html"])
    assert len(out) == 1, out


def test_errata_latest_for_another_work_product_still_blocks():
    out = _stage_token(["https://docs.oasis-open.org/csaf/csaf/v2.0/errata01/"
                        "csaf-v2.0-errata01.html"])
    assert len(out) == 1, out


def test_errata_latest_with_a_bare_stage_word_still_blocks():
    for tail in ("-os", "-csd", "-cs01", "-complete-os"):
        out = _stage_token([f"{BASE}/OpenDocument-v1.4-errata01{tail}.html"])
        assert len(out) == 1, (tail, out)


def test_errata_latest_with_a_malformed_name_still_blocks():
    for u in (f"{BASE}/errata01.html", f"{BASE}/Foo-v9.9-errata01.html",
              "https://docs.oasis-open.org/office/OpenDocument/errata01/"
              "OpenDocument-v1.4-errata01.html"):
        assert len(_stage_token([u])) == 1, u


def test_distant_version_ancestor_is_not_the_package_version(tmp_path):
    stage = tmp_path / "MyWork" / "v2.0" / "batch" / "office" / "odf" / "csd01"
    stage.mkdir(parents=True)
    (stage / "MyWork-v2.0-csd01.html").write_text("x", encoding="utf-8")
    f = pc.Findings()
    pc.check_hygiene(str(stage), f, {"MyWork-v2.0-csd01.html"})
    assert [i["severity"] for i in f.items if i["check"] == "case"] == ["BLOCKER"]


def _hygiene(tmp_path, names, wp="OpenDocument", ver="v1.4", tail=("errata01", "csd01")):
    stage = tmp_path.joinpath("office", wp, ver, *tail)
    stage.mkdir(parents=True)
    for n in names:
        (stage / n).write_text("x", encoding="utf-8")
    f = pc.Findings()
    pc.check_hygiene(str(stage), f, set(names))
    return [i for i in f.items if i["check"] == "case"]


def test_odf_mixed_case_delivery_names_pass(tmp_path):
    names = ODF_NAMES + ["OpenDocument-v1.4-errata01-csd01.zip",
                         "OpenDocument-v1.4-errata01-csd01-manifest.txt"]
    assert _hygiene(tmp_path, names) == []


def test_mixed_case_outside_the_wp_abbrev_still_blocks(tmp_path):
    for k, bad in enumerate(("OpenDocument-V1.4-errata01-csd01.html",
                "OpenDocument-v1.4-Errata01-csd01.html",
                "OpenDocument-v1.4-errata01-CSD01.html",
                "OpenDocument-v1.4-errata01-csd01.HTML",
                "OpenDocument-v1.4-errata01-csd01-Redline.html")):
        sub = tmp_path / f"case{k}"   # the macOS temp filesystem folds case
        out = _hygiene(sub, [bad])
        assert [i["severity"] for i in out] == ["BLOCKER"], (bad, out)


def test_wp_abbrev_not_matching_the_directory_still_blocks(tmp_path):
    assert [i["severity"] for i in _hygiene(tmp_path, ["OpenDocument-v1.4-csd01.html"],
                                            wp="opendocument", tail=("csd01",))] == ["BLOCKER"]


def test_wp_abbrev_case_differing_from_directory_still_blocks(tmp_path):
    assert [i["severity"] for i in _hygiene(tmp_path, ["OpenDocument-v1.4-csd01.html"],
                                            wp="Opendocument", tail=("csd01",))] == ["BLOCKER"]


def test_mixed_case_name_that_is_not_a_document_identifier_still_blocks(tmp_path):
    assert [i["severity"] for i in _hygiene(tmp_path, ["OpenDocument.html"],
                                            tail=("csd01",))] == ["BLOCKER"]


def test_mixed_case_without_a_version_directory_still_blocks(tmp_path):
    stage = tmp_path / "OpenDocument" / "csd01"
    stage.mkdir(parents=True)
    (stage / "OpenDocument-v1.4-csd01.html").write_text("x", encoding="utf-8")
    f = pc.Findings()
    pc.check_hygiene(str(stage), f, {"OpenDocument-v1.4-csd01.html"})
    assert [i["severity"] for i in f.items if i["check"] == "case"] == ["BLOCKER"]
