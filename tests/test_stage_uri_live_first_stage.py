"""stage-uri-live: the first stage of a new version may cite Latest-stage
URIs in its own version root, which its publication creates. Every other
Previous- or Latest-stage URI must still retrieve.

DMLex v1.1 wd01 (Sep 2026) cited .../v1.1/dmlex-v1.1.html as its Latest stage
and was blocked, as the first stage of every new version would be. The
exemption keys on the version root being absent from the site; an earlier
draft keyed on the Previous-stage line, and an adversarial review showed a
mis-cited Previous stage could then hide a broken Latest URI.
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


class FakeResponse:
    status = 200
    def __enter__(self): return self
    def __exit__(self, *a): return False


@pytest.fixture
def site(monkeypatch):
    """Answer 200 for the URLs in `live`, 404 for everything else."""
    live: set = set()
    def fake(req, timeout=None):
        if req.full_url in live:
            return FakeResponse()
        raise urllib.error.HTTPError(req.full_url, 404, "Not Found", {}, None)
    monkeypatch.setattr(urllib.request, "urlopen", fake)
    monkeypatch.delenv("PUB_CHECK_OFFLINE", raising=False)
    return live


def blocked(md):
    f = oasis_pub_check.Findings()
    oasis_pub_check.check_stage_uri_reachability(md, f)
    return [x["message"] for x in f.items if x["severity"] == "BLOCKER"]


def test_first_stage_of_an_unpublished_version_may_cite_its_own_latest(site):
    site.add(f"{D}/v1.0/os/spec-v1.0-os.html")
    msgs = blocked(cover(f"{D}/v1.1/wd01/spec-v1.1-wd01.html",
                         f"{D}/v1.0/os/spec-v1.0-os.html",
                         f"{D}/v1.1/spec-v1.1.html"))
    assert msgs == [], msgs


def test_a_published_version_root_still_needs_its_latest(site):
    site.update({f"{D}/v1.1/", f"{D}/v1.1/csd01/spec-v1.1-csd01.html"})
    msgs = blocked(cover(f"{D}/v1.1/csd02/spec-v1.1-csd02.html",
                         f"{D}/v1.1/csd01/spec-v1.1-csd01.html",
                         f"{D}/v1.1/spec-v1.1.html"))
    assert any("Latest stage" in m for m in msgs), msgs


def test_a_mis_cited_previous_stage_does_not_hide_a_broken_latest(site):
    # A later stage of a published version that cites the wrong Previous
    # stage: the Latest URI is broken and must still be reported.
    site.update({f"{D}/v1.1/", f"{D}/v1.0/os/spec-v1.0-os.html"})
    msgs = blocked(cover(f"{D}/v1.1/csd02/spec-v1.1-csd02.html",
                         f"{D}/v1.0/os/spec-v1.0-os.html",
                         f"{D}/v1.1/spec-v1.1.htm"))
    assert any("Latest stage" in m for m in msgs), msgs


def test_a_latest_outside_the_own_version_root_still_needs_to_exist(site):
    msgs = blocked(cover(f"{D}/v1.1/wd01/spec-v1.1-wd01.html", "N/A",
                         f"{D}/v1.0/spec-v1.0.html"))
    assert any("Latest stage" in m for m in msgs), msgs
