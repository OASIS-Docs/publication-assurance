# Copyright 2026 OASIS Open
# SPDX-License-Identifier: Apache-2.0
# Authored by Michael Coletta, Technical Advisor to OASIS Open.
"""front-matter and stage-uri-live: cover URLs written as Markdown autolinks.

SARIF v2.2 csd01 and the CSAF v2.1 draft (Oct 2026) write each cover URL as
<https://...>, the form the md-links warning recommends. The stage-URL parser
kept the closing '>', so 'csaf-v2.1-csd04.md>' was "not a file in the
package" and every Previous/Latest URI "returned HTTP 404".
"""

from __future__ import annotations

from conftest import oasis_pub_check

BASE = "https://docs.oasis-open.org/csaf/csaf/v2.1"

COVER = f"""# Common Security Advisory Framework Version 2.1

## Committee Specification Draft 04

#### This stage:
<{BASE}/csd04/csaf-v2.1-csd04.md> (Authoritative) \\
<{BASE}/csd04/csaf-v2.1-csd04.html> \\
<{BASE}/csd04/csaf-v2.1-csd04.pdf>

#### Previous stage:
<{BASE}/csd03/csaf-v2.1-csd03.md> (Authoritative) \\
<{BASE}/csd03/csaf-v2.1-csd03.html> \\
<{BASE}/csd03/csaf-v2.1-csd03.pdf>

#### Latest stage:
<{BASE}/csaf-v2.1.md> (Authoritative) \\
<{BASE}/csaf-v2.1.html> \\
<{BASE}/csaf-v2.1.pdf>

#### Technical Committee:
"""


def test_autolinked_cover_urls_parse_without_the_closing_bracket():
    urls = {h: oasis_pub_check.stage_urls_from_md(COVER, h)
            for h in ("This", "Previous", "Latest")}
    assert urls == {
        "This": [f"{BASE}/csd04/csaf-v2.1-csd04.{e}" for e in ("md", "html", "pdf")],
        "Previous": [f"{BASE}/csd03/csaf-v2.1-csd03.{e}" for e in ("md", "html", "pdf")],
        "Latest": [f"{BASE}/csaf-v2.1.{e}" for e in ("md", "html", "pdf")],
    }


def test_an_autolinked_redirect_url_is_reported_without_the_bracket():
    m = oasis_pub_check.URI_ALIAS_BARE_URL_RE.search("See <https://bit.ly/abc> on oasis-open.org.")
    assert m.group(0) == "https://bit.ly/abc"
