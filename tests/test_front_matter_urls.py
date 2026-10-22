# Copyright 2026 OASIS Open
# SPDX-License-Identifier: Apache-2.0
# Authored by Michael Coletta, Technical Advisor to OASIS Open.
"""version-refs: a URL ends where a Markdown autolink ends, only this work
product's own URLs are compared by version, and a References entry is a
deliberate citation.

A References entry cites <https://docs.oasis-open.org/...>. The version check
read the URL through the closing '>', so each message printed the URL with a
stray '>', and the URL did not match the same URL cited bare in Related work,
which the check exempts (CSAF v2.1 csd03, Sep 2026).

This scan reads the whole Markdown, so since Oct 2026 it is its own class,
version-refs, not part of front-matter. A URL that appears only in a
References section is recorded, not warned on (CSAF v2.1 csd04 cited CSAF
CVRF v1.2 only in Informative References). OTHER is therefore cited in body
prose as well as in References, and the message names that prose line.
"""

from __future__ import annotations

from conftest import oasis_pub_check

OLD = "https://docs.oasis-open.org/wid/wid/v1.0/os/wid-v1.0-os.html"
# A different version of THIS work product (wid/wid), cited only in
# References: the stale-draft tell the check exists for.
OTHER = "https://docs.oasis-open.org/wid/wid/v0.9/wid-v0.9.html"
# A different work product of the same TC (wid/wid-legacy): an external
# citation whose version says nothing about this draft (CSAF CVRF v1.2 cited
# by CSAF v2.1 csd04, Oct 2026).
SIBLING = "https://docs.oasis-open.org/wid/wid-legacy/v1.2/cs01/wid-legacy-v1.2-cs01.html"
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

# 1 Introduction

This draft revises an earlier one (<{OTHER}>).

# References

**[WID-v1.0]** _Widget Version 1.0_. <{OLD}>.

**[WID-v0.9]** _Widget Version 0.9_. <{OTHER}>.

**[WID-LEGACY-v1.2]** _Widget Legacy Version 1.2_. <{SIBLING}>.
"""


def warnings(md=MD):
    f = oasis_pub_check.Findings()
    oasis_pub_check.check_version_refs(md, "v2.0", f)
    return [x["message"] for x in f.items if x["check"] == "version-refs"]


def other_line():
    return next(i for i, l in enumerate(MD.splitlines(), 1) if OTHER in l)


def test_messages_carry_the_url_without_the_autolink_bracket():
    got = warnings()
    assert got and not any(u.endswith(">") for m in got for u in m.split() if "://" in u), got


def test_a_url_cited_in_related_work_is_exempt_wherever_it_is_cited():
    got = warnings()
    assert got == [f"Line {other_line()} (section '1 Introduction'): links to version v0.9 "
                   f"of this work product (package is v2.0): {OTHER}. Confirm the link is "
                   f"meant to point at that other version; if not, change it to this "
                   f"version's address."]


def test_a_different_work_product_of_the_same_tc_is_not_a_version_mismatch():
    # Naming Directives v1.7 s6.1: docs.oasis-open.org/[tc-shortname]/
    # [WP-abbrev]/[version-id]/... A URL under another WP-abbrev is another
    # specification, so its version is not compared with this package's.
    got = warnings()
    assert not any(SIBLING in m for m in got), got


def test_another_work_product_cited_in_body_prose_is_not_compared():
    md = MD.split("# References")[0] + f"See also <{SIBLING}>.\n"
    assert not any(SIBLING in m for m in warnings(md))


def test_a_stale_http_link_to_this_work_product_still_warns():
    # The This-stage block is https (anything else is a blocker); an older
    # copied link may be http. The work-product prefix ignores the scheme.
    stale = "http://docs.oasis-open.org/wid/wid/v1.0/os/wid-v1.0-os.html"
    md = MD.split("#### Related work")[0] + f"#### Citation format\n{stale}\n"
    assert any(stale in m for m in warnings(md))


def test_a_url_cited_only_in_a_references_section_is_recorded_not_warned_on():
    """The CSAF v2.1 csd04 shape: a References subsection under a numbered
    section, the URL in an autolink, the next numbered subsection after it."""
    md = MD.split("# 1 Introduction")[0] + (
        "# 1 Introduction\n\nText.\n\n## 1.3 Normative References\n\nText.\n\n"
        f"## 1.4 Informative References\n\n**[WID-v0.9]** _Widget 0.9_. <{OTHER}>.\n\n"
        "## 1.5 Typographical Conventions\n\nText.\n")
    f = oasis_pub_check.Findings()
    oasis_pub_check.check_version_refs(md, "v2.0", f)
    assert [x for x in f.items if x["check"] == "version-refs"] == []
    assert OTHER in f.observed["version-refs"]["other_versions_cited_in_references"]


def test_the_same_url_after_the_references_section_ends_still_warns():
    md = MD.split("# 1 Introduction")[0] + (
        "# 1 Introduction\n\n## 1.4 Informative References\n\nNone.\n\n"
        f"## 1.5 Typographical Conventions\n\nSee <{OTHER}>.\n")
    got = warnings(md)
    assert len(got) == 1 and "(section '1.5 Typographical Conventions')" in got[0], got


def test_front_matter_no_longer_reports_another_version():
    f = oasis_pub_check.Findings()
    oasis_pub_check.check_front_matter(MD, {"md": "/x/wid-v2.0-csd01.md"}, "v2.0", "csd01", f)
    assert not [x for x in f.items if x["check"] == "front-matter" and OTHER in x["message"]]
