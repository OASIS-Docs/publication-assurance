"""package-refs: files and directories the document cites under its own stage
path must ship in the package.

A cited directory (a URL ending in "/", such as a schemas/ index) is present
when the directory is. Checking it as a file reported every staged directory
missing: the DMLex v1.0 OS package, staged with its schemas/ tree, drew five
false blockers (Sep 2026).
"""

from __future__ import annotations

from conftest import oasis_pub_check

BASE = "https://docs.oasis-open.org/tc/spec/v1.0/os/"


def _blockers(stage, md_text):
    f = oasis_pub_check.Findings()
    oasis_pub_check.check_correction_classes(md_text, str(stage), BASE, "os", f)
    return [x for x in f.items if x["check"] == "package-refs"]


def test_a_cited_directory_that_ships_is_not_reported(tmp_path):
    (tmp_path / "schemas" / "JSON").mkdir(parents=True)
    (tmp_path / "schemas" / "JSON" / "spec.schema.json").write_text("{}")
    md = (f"Artifacts: <{BASE}schemas/> and <{BASE}schemas/JSON/>, "
          f"schema <{BASE}schemas/JSON/spec.schema.json>.")
    found = _blockers(tmp_path, md)
    assert found == [], f"shipped directories reported missing: {[x["message"] for x in found]}"


def test_a_cited_directory_that_is_absent_is_still_a_blocker(tmp_path):
    md = f"Artifacts: <{BASE}schemas/XML/>."
    found = _blockers(tmp_path, md)
    assert len(found) == 1 and "'schemas/XML/'" in found[0]["message"], (
        f"an absent cited directory was not reported: {[x["message"] for x in found]}"
    )


def test_a_cited_file_that_is_absent_is_still_a_blocker(tmp_path):
    (tmp_path / "schemas").mkdir()
    md = f"Schema: <{BASE}schemas/spec.xsd>."
    found = _blockers(tmp_path, md)
    assert len(found) == 1 and "'schemas/spec.xsd'" in found[0]["message"], (
        f"an absent cited file was not reported: {[x["message"] for x in found]}"
    )
