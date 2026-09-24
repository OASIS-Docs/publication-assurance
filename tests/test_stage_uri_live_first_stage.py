"""stage-uri-live: Previous- and Latest-stage URIs must retrieve, except the
Latest-stage URIs that the first stage of a new version creates itself.

DMLex v1.1 wd01 (Sep 2026) cited .../v1.1/dmlex-v1.1.html as its Latest
stage. That file is created by the version's first publication, so it 404s
beforehand, and the gate blocked what would block the first stage of every
new version. Every URI is answered 404 here, so the tests assert which URIs
the check treats as defects without touching the network.
"""

from __future__ import annotations

import urllib.error
import urllib.request

import pytest

from conftest import oasis_pub_check

D = "https://docs.oasis-open.org/tc/spec"


def cover(this, previous, latest):
    return (f"# Spec\n\n#### This stage:\n\n{this}\n\n#### Previous stage:\n\n"
            f"{previous}\n\n#### Latest stage:\n\n{latest}\n\n#### Technical Committee:\n")


@pytest.fixture
def everything_404(monkeypatch):
    def fake(req, timeout=None):
        raise urllib.error.HTTPError(req.full_url, 404, "Not Found", {}, None)
    monkeypatch.setattr(urllib.request, "urlopen", fake)
    monkeypatch.delenv("PUB_CHECK_OFFLINE", raising=False)


def blocked(md):
    f = oasis_pub_check.Findings()
    oasis_pub_check.check_stage_uri_reachability(md, f)
    return [x["message"] for x in f.items if x["severity"] == "BLOCKER"]


def test_first_stage_of_a_version_may_cite_its_own_latest_root(everything_404):
    md = cover(f"{D}/v1.1/wd01/spec-v1.1-wd01.html",
               f"{D}/v1.0/os/spec-v1.0-os.html",
               f"{D}/v1.1/spec-v1.1.html")
    msgs = blocked(md)
    assert not any("Latest stage" in m for m in msgs), msgs
    assert any("Previous stage" in m for m in msgs), (
        f"the Previous-stage 404 must still block: {msgs}")


def test_a_later_stage_of_the_same_version_still_needs_its_latest(everything_404):
    md = cover(f"{D}/v1.1/csd02/spec-v1.1-csd02.html",
               f"{D}/v1.1/csd01/spec-v1.1-csd01.html",
               f"{D}/v1.1/spec-v1.1.html")
    msgs = blocked(md)
    assert any("Latest stage" in m for m in msgs), (
        f"a missing Latest root after csd01 was not reported: {msgs}")


def test_a_latest_outside_the_own_version_root_still_needs_to_exist(everything_404):
    md = cover(f"{D}/v1.1/wd01/spec-v1.1-wd01.html",
               "N/A",
               f"{D}/v1.0/spec-v1.0.html")
    msgs = blocked(md)
    assert any("Latest stage" in m for m in msgs), msgs
