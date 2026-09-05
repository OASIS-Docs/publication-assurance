"""The policy authority behind each check, verified rather than asserted.

`AUTHORITIES.md` quotes OASIS policy at 94 check signatures. Until now the
corpus those quotes came from did not ship, so a TC could not check a single
one, and the file pointed at a `corpus/MANIFEST.json` that was not in the
repository. The corpus, the crosswalk and the criteria ship now, and this file
is what makes the claim checkable rather than editorial:

- every sha256 in the manifest matches the file it names;
- every quote in `authorities.yaml` is a verbatim substring of the `.txt` it
  cites, whitespace-normalised the way the extraction was;
- every criterion a crosswalk entry references exists in `criteria.yaml`;
- the crosswalk and the tool's own condition registry name the same conditions,
  in both directions, so a check added without a crosswalk decision fails here.
"""

from __future__ import annotations

import hashlib
import json
import re
import pathlib

import pytest
import yaml   # a hard dependency on purpose: a skipped authority check proves nothing

from conftest import REPO_ROOT, oasis_pub_check

PUB = REPO_ROOT / "pub-check"
CORPUS = PUB / "corpus"

MANIFEST = json.loads((CORPUS / "MANIFEST.json").read_text(encoding="utf-8"))
CROSSWALK = json.loads((PUB / "crosswalk.json").read_text(encoding="utf-8"))
CRITERIA = {c["id"]: c
            for c in yaml.safe_load((PUB / "criteria.yaml").read_text(encoding="utf-8"))["criteria"]}
AUTHORITIES = yaml.safe_load((PUB / "authorities.yaml").read_text(encoding="utf-8"))

REGISTRY = {(d["check"], d["sig"]): d for d in oasis_pub_check.CONDITION_DOCS}


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s)


def _text(doc: str) -> str:
    return _norm((CORPUS / doc).read_text(encoding="utf-8"))


@pytest.mark.parametrize("name", sorted(MANIFEST["documents"]))
def test_every_snapshot_matches_its_recorded_digest(name):
    """A hash in a manifest whose file is absent, or altered, proves nothing."""
    path = CORPUS / name
    assert path.exists(), f"{name} is in MANIFEST.json but not in corpus/"
    got = hashlib.sha256(path.read_bytes()).hexdigest()
    assert got == MANIFEST["documents"][name]["sha256"], (
        f"{name} does not match its recorded sha256; the snapshot was altered "
        f"after it was pinned.")


@pytest.mark.parametrize("name", sorted(MANIFEST["documents"]))
def test_every_snapshot_has_its_text_extraction(name):
    text_file = MANIFEST["documents"][name]["text_file"]
    assert (CORPUS / text_file).exists(), f"{text_file} is missing from corpus/"


def test_every_quoted_clause_is_verbatim_in_its_source():
    """The load-bearing claim of the whole catalog."""
    bad = []
    checked = 0
    for key, rec in AUTHORITIES["conditions"].items():
        for a in rec["authorities"]:
            checked += 1
            doc = a["doc"]
            if not (CORPUS / doc).exists():
                bad.append(f"{key}: cites {doc}, which is not in corpus/")
                continue
            if _norm(a["quote"]) not in _text(doc):
                bad.append(f"{key}: quote is not verbatim in {doc}: {a['quote'][:70]}...")
    assert checked > 200, f"only {checked} quotes examined; the catalog should carry far more"
    assert not bad, "\n".join(bad[:10])


def test_every_referenced_criterion_exists():
    missing = sorted({cid
                      for c in CROSSWALK["conditions"] if c["status"] == "policy-grounded"
                      for cid in c.get("criteria", [])
                      if cid not in CRITERIA})
    assert not missing, f"crosswalk references criteria that criteria.yaml does not define: {missing}"


def test_the_crosswalk_and_the_registry_agree_in_both_directions():
    """A check added without an authority decision must fail here, which is how
    the crosswalk fell a condition behind for twelve days before."""
    have = {(c["check"], c["sig"]) for c in CROSSWALK["conditions"]}
    missing = sorted(set(REGISTRY) - have)
    stale = sorted(have - set(REGISTRY))
    assert not missing, (
        f"conditions in the tool with no crosswalk entry: {missing}. Run "
        f"_admin/authority-mapping/sync_crosswalk.py, decide whether each is "
        f"policy-grounded, then re-run gen_authorities.py.")
    assert not stale, f"crosswalk entries for conditions the tool no longer has: {stale}"


def test_the_advertised_grounding_counts_are_the_measured_ones():
    grounded_sigs = [(c["check"], c["sig"]) for c in CROSSWALK["conditions"]
                     if c["status"] == "policy-grounded"]
    grounded = sum(REGISTRY[k].get("sites", 1) for k in grounded_sigs)
    total = sum(d.get("sites", 1) for d in REGISTRY.values())

    catalog = (PUB / "AUTHORITIES.md").read_text(encoding="utf-8")
    assert f"Of the {total} individual check conditions" in catalog
    assert f"**{grounded} are grounded in written policy**" in catalog
    assert f"appearing below as {len(grounded_sigs)} catalog entries" in catalog

    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    flat = re.sub(r"\s+", " ", readme)
    assert f"{grounded} of the {total} checks" in flat, (
        f"README.md does not advertise the measured {grounded} of {total}")


def test_authorities_yaml_and_the_catalog_cover_the_same_conditions():
    yaml_keys = set(AUTHORITIES["conditions"])
    cw_keys = {f"{c['check']}/{c['sig']}" for c in CROSSWALK["conditions"]
               if c["status"] == "policy-grounded"}
    assert yaml_keys == cw_keys, (
        "authorities.yaml and crosswalk.json disagree about which conditions are "
        "policy-grounded; re-run gen_authorities.py")
