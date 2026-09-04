"""Regression fixtures for stage-uri-live, the v1.2.0 check class.

The Previous-stage and Latest-stage cover blocks name files that are not in
the package, so every other check can see only their shape. This class fetches
them, and its whole design rests on one distinction: a definitive 404/410 is a
publication defect, and everything else the network can do to a request is not.
A check that blocked on a timeout would manufacture defects from a flaky
runner, which is worse than the gap it was written to close.

These tests stub urllib.request.urlopen. The check imports urllib.request
inside the function body, so patching the module attribute reaches it.
"""

from __future__ import annotations

import urllib.error
import urllib.request

import pytest

from conftest import oasis_pub_check

check = oasis_pub_check.check_stage_uri_reachability
Findings = oasis_pub_check.Findings
BLOCKER, INFO = oasis_pub_check.BLOCKER, oasis_pub_check.INFO
SITE = oasis_pub_check.SITE

# stage_urls_from_md reads the block between a stage heading and the next
# heading, so the trailing heading is load-bearing, not decoration.
COVER = f"""# Example Specification Version 1.0

## Previous Stage

{SITE}/example/v1.0/csd01/example-v1.0-csd01.docx

## Latest Stage

{SITE}/example/v1.0/example-v1.0.html

## Technical Committee
"""


class _Response:
    def __init__(self, status): self.status = status
    def __enter__(self): return self
    def __exit__(self, *exc): return False


def _urlopen_returning(status):
    def _open(req, timeout=None):
        return _Response(status)
    return _open


def _urlopen_raising(exc):
    def _open(req, timeout=None):
        raise exc
    return _open


def _http_error(code):
    return urllib.error.HTTPError(
        url="http://example.invalid", code=code, msg="stub", hdrs=None, fp=None)


def _run(monkeypatch, opener, md=COVER, offline=False):
    monkeypatch.setattr(urllib.request, "urlopen", opener)
    monkeypatch.delenv("PUB_CHECK_OFFLINE", raising=False)
    if offline:
        monkeypatch.setenv("PUB_CHECK_OFFLINE", "1")
    f = Findings()
    check(md, f)
    return f


def _sev(f, severity):
    return [i for i in f.items if i["severity"] == severity
            and i["check"] == "stage-uri-live"]


def test_a_404_previous_stage_uri_is_a_blocker(monkeypatch):
    """The OData csd03 defect: the cover cited csd02 as .docx, csd02 went
    markdown-native, and the citation 404d on the live site while passing every
    shape check."""
    f = _run(monkeypatch, _urlopen_raising(_http_error(404)))
    blockers = _sev(f, BLOCKER)
    assert len(blockers) == 2, [i["message"] for i in f.items]
    assert any("Previous stage" in i["message"] for i in blockers)
    assert any("Latest stage" in i["message"] for i in blockers)


def test_a_410_is_also_a_blocker(monkeypatch):
    f = _run(monkeypatch, _urlopen_raising(_http_error(410)))
    assert len(_sev(f, BLOCKER)) == 2


def test_a_200_raises_nothing(monkeypatch):
    f = _run(monkeypatch, _urlopen_returning(200))
    assert f.items == []
    assert f.observed["stage-uri-live"]["stage_uris_fetched"] == "2"


def test_a_transport_failure_is_info_not_a_blocker(monkeypatch):
    """A DNS failure or timeout must not manufacture a publication defect."""
    f = _run(monkeypatch, _urlopen_raising(urllib.error.URLError("dns")))
    assert _sev(f, BLOCKER) == []
    assert len(_sev(f, INFO)) == 2
    assert all("not a 404" in i["message"] for i in _sev(f, INFO))


def test_a_5xx_is_info_not_a_blocker(monkeypatch):
    """A bot challenge or transient 5xx is not evidence the document is gone."""
    f = _run(monkeypatch, _urlopen_raising(_http_error(503)))
    assert _sev(f, BLOCKER) == []
    assert len(_sev(f, INFO)) == 2


def test_offline_is_a_silent_no_op_and_makes_no_request(monkeypatch):
    """PUB_CHECK_OFFLINE must short-circuit before the first request, matching
    the other live-site checks. The opener fails the test if it is reached."""
    def _boom(req, timeout=None):
        raise AssertionError("network reached under PUB_CHECK_OFFLINE")
    f = _run(monkeypatch, _boom, offline=True)
    assert f.items == []


def test_an_off_site_uri_is_not_fetched(monkeypatch):
    """Shape checks own off-site URIs; this class only speaks for the
    publication host, so a TC's own mirror must not be probed."""
    md = COVER.replace(f"{SITE}/example/v1.0/example-v1.0.html",
                       "https://example.org/mirror/example-v1.0.html")
    f = _run(monkeypatch, _urlopen_raising(_http_error(404)), md=md)
    assert f.observed["stage-uri-live"]["stage_uris_fetched"] == "1"
    assert len(_sev(f, BLOCKER)) == 1
    assert "Previous stage" in _sev(f, BLOCKER)[0]["message"]


def test_a_cover_with_no_stage_blocks_makes_no_request(monkeypatch):
    def _boom(req, timeout=None):
        raise AssertionError("network reached with no stage URIs to check")
    f = _run(monkeypatch, _boom, md="# Title\n\n## Technical Committee\n")
    assert f.items == []
