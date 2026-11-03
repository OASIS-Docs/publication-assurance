# Copyright 2026 OASIS Open
# SPDX-License-Identifier: Apache-2.0
# Authored by Michael Coletta, Technical Advisor to OASIS Open.
"""vml-fallback counts pictures, not every VML shape.

AKN (LegalDocML) Core v2.0 OS Part 2, Word HTML export of 3 Nov 2026: the
check counted nine v:imagedata and one <![if !vml]><img> fallback and blocked.
The one picture, the cover logo, had its fallback. The other eight were
Word's horizontal-line shapes before each chapter, inside
[if mso & !supportInlineShapes] field code, with no src: there is no picture
for a browser to lose. The excerpts below are copied from that file.
"""

from __future__ import annotations

from conftest import oasis_pub_check

COVER_LOGO = """<!--[if gte vml 1]><v:shape id="image1.png" o:spid="_x0000_i1033" type="#_x0000_t75"
 style='width:230pt;height:47pt;visibility:visible;mso-wrap-style:square'>
 <v:imagedata src="akn-core-v2.0-os-part2-specs.fld/image001.png" o:title=""/>
</v:shape><![endif]--><![if !vml]><img width=230 height=47
src="akn-core-v2.0-os-part2-specs.fld/image001.png" v:shapes="image1.png"><![endif]>"""

LOGO_WITHOUT_FALLBACK = """<!--[if gte vml 1]><v:shape id="image1.png" type="#_x0000_t75"
 style='width:230pt;height:47pt'>
 <v:imagedata src="x.fld/image001.png" o:title=""/>
</v:shape><![endif]-->"""

HORIZONTAL_LINE = """<!--[if mso & !supportInlineShapes & supportFields]><v:shape
 id="_x0000_i1032" type="#_x0000_t75" style='width:0;height:1.5pt'>
 <v:imagedata croptop="-65520f" cropbottom="65520f"/>
</v:shape><span style='mso-element:field-end'></span><![endif]-->"""


def _blockers(html: str) -> list[dict]:
    f = oasis_pub_check.Findings()
    oasis_pub_check.check_vml_fallback(html, f)
    return [x for x in f.items if x["check"] == "vml-fallback" and x["severity"] == "BLOCKER"]


def test_horizontal_line_shapes_without_a_picture_do_not_block():
    html = "<html><body>" + COVER_LOGO + HORIZONTAL_LINE * 8 + "</body></html>"
    assert _blockers(html) == []


def test_a_vml_picture_with_no_fallback_still_blocks():
    """The class the check exists for (PKCS#11 v3.2 os, KMIP v3.0 csd01 covers)."""
    html = "<html><body>" + LOGO_WITHOUT_FALLBACK + HORIZONTAL_LINE * 8 + "</body></html>"
    assert len(_blockers(html)) == 1
