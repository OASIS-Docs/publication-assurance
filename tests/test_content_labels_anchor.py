# Copyright 2026 OASIS Open
# SPDX-License-Identifier: Apache-2.0
# Authored by Michael Coletta, Technical Advisor to OASIS Open.
"""content-labels reads a heading's label before any anchor that follows it.

The DMLex Markdown edition writes every heading as "Appendix A ... (Informative)
<a id='...'></a>". The label test is anchored at the end of the title, so the
anchor hid it: the gate reported eight appendices as unlabelled and warned on
an Examples heading, all labelled (Sep 2026).
"""

from __future__ import annotations

import pytest

from conftest import oasis_pub_check


def findings(md):
    f = oasis_pub_check.Findings()
    oasis_pub_check.check_content_labels(md, "", "csd01", f)
    return [x["message"] for x in f.items if x["check"] == "content-labels"]


@pytest.mark.parametrize("anchor", ["<a id='appx-a'></a>", "{#appx-a}", "<a id=\"appx-a\"></a> <span id='x'></span>"])
def test_a_label_before_an_anchor_is_read(anchor):
    md = (f"# 1 Introduction\n\nText.\n\n# Appendix A Examples of use (Informative) {anchor}\n\nText.\n\n"
          f"## A.1 Examples (Non-normative) {anchor.replace('appx-a', 'ex')}\n\nText.\n")
    assert findings(md) == []


def test_an_unlabelled_heading_with_an_anchor_is_still_reported():
    md = "# 1 Introduction\n\nText.\n\n# Appendix A Examples of use <a id='appx-a'></a>\n\nText.\n"
    assert len(findings(md)) == 1
