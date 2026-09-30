# Copyright 2026 OASIS Open
# SPDX-License-Identifier: Apache-2.0
# Authored by Michael Coletta, Technical Advisor to OASIS Open.
"""public-review-metadata: the advisory note states what it observed.

With no evidence that the revision went to public review, the note said the
companion file "must be present", while the listing recorded beside it showed
the file present and live (CSAF v2.1 csd03, Sep 2026). The live directory is
served here by a stub, so the test needs no network.
"""

from __future__ import annotations

import urllib.request

import pytest

from conftest import oasis_pub_check

BASE = "https://docs.oasis-open.org/wid/wid/v1.0/csd02/"
STEM = "wid-v1.0-csd02"


class _Reply:
    def __init__(self, body):
        self.status, self._body = 200, body.encode()

    def read(self, n=-1):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def serve(monkeypatch, names):
    listing = "".join(f'<a href="{n}">{n}</a>' for n in names)

    def urlopen(req, timeout=None):
        url = req.full_url
        if url == BASE:
            return _Reply(listing)
        raise urllib.error.HTTPError(url, 404, "not found", {}, None)

    monkeypatch.setattr(urllib.request, "urlopen", urlopen)
    monkeypatch.delenv("PUB_CHECK_OFFLINE", raising=False)
    monkeypatch.delenv("PUB_CHECK_PUBLIC_REVIEW_OPEN", raising=False)


def note(monkeypatch, names):
    serve(monkeypatch, names)
    f = oasis_pub_check.Findings()
    oasis_pub_check.check_public_review_metadata(BASE, "csd02", STEM, f)
    got = [x for x in f.items if x["check"] == "public-review-metadata"]
    assert [x["severity"] for x in got] == ["INFO"]
    return got[0]["message"]


def test_a_present_companion_file_is_reported_present(monkeypatch):
    msg = note(monkeypatch, [f"{STEM}.html", f"{STEM}-public-review-metadata.html"])
    assert "must be present" not in msg
    assert f"{STEM}-public-review-metadata.html is present in the live stage directory" in msg


def test_an_absent_companion_file_is_reported_absent(monkeypatch):
    msg = note(monkeypatch, [f"{STEM}.html"])
    assert f"{STEM}-public-review-metadata.html is not in the live stage directory" in msg
    assert "must be present" in msg
