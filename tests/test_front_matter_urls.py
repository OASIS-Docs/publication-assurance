# Copyright 2026 OASIS Open
# SPDX-License-Identifier: Apache-2.0
# Authored by Michael Coletta, Technical Advisor to OASIS Open.
"""front-matter: a URL ends where a Markdown autolink ends.

A References entry cites <https://docs.oasis-open.org/...>. The version check
read the URL through the closing '>', so each message printed the URL with a
stray '>', and the URL did not match the same URL cited bare in Related work,
which the check exempts (CSAF v2.1 csd03, Sep 2026).
"""

from __future__ import annotations

from conftest import oasis_pub_check

OLD = "https://docs.oasis-open.org/wid/wid/v1.0/os/wid-v1.0-os.html"
OTHER = "https://docs.oasis-open.org/wid/gadget/v3.0/gadget-v3.0.html"
MD = f"""# Widget Version 2.0

#### This stage
https://docs.oasis-open.org/wid/wid/v2.0/csd01/wid-v2.0-csd01.md

#### Latest stage
https://docs.oasis-open.org/wid/wid/v2.0/wid-v2.0.md

#### Related work
This specification replaces:

- _Widget Version 1.0_. OASIS Standard. {OLD}.

#### Abstract
Text.

# References

**[WID-v1.0]** _Widget Version 1.0_. <{OLD}>.

**[GADGET]** _Gadget Version 3.0_. <{OTHER}>.
"""


def warnings():
    f = oasis_pub_check.Findings()
    items = {"md": "/x/wid-v2.0-csd01.md"}
    oasis_pub_check.check_front_matter(MD, items, "v2.0", "csd01", f)
    return [x["message"] for x in f.items
            if x["check"] == "front-matter" and "declares version" in x["message"]]


def test_messages_carry_the_url_without_the_autolink_bracket():
    got = warnings()
    assert got and not any(">" in m.split(" -- ")[0] for m in got), got


def test_a_url_cited_in_related_work_is_exempt_wherever_it_is_cited():
    got = warnings()
    assert got == [f"URL declares version v3.0 (package is v2.0): {OTHER} "
                   "-- confirm this is an intentional external reference."]
