# Copyright 2026 OASIS Open
# SPDX-License-Identifier: Apache-2.0
# Authored by Michael Coletta, Technical Advisor to OASIS Open.
"""content-labels reads the status sentence the OASIS starter template puts
under an appendix or annex title.

The current OASIS starter template (v1.05) opens every appendix with
"(This appendix does not form an integral part of this Specification and is
informational.)" and every annex with "(This annex forms an integral part of
this Specification.)", the ITU-T drafting convention. CSAF v2.1 CSD04 used the
first sentence on Appendices A, B and D and "This appendix provides informative
guidance on ..." on Appendix C. The check reported all four as carrying no
content-type label (22 Oct 2026): the leading parenthesis hid the lead, the
word "informational" was not a marker, "provides" was not an accepted lead
verb, and the annex sentence has no marker word at all.
"""

from __future__ import annotations

import pytest

from conftest import oasis_pub_check


def findings(md):
    f = oasis_pub_check.Findings()
    oasis_pub_check.check_content_labels(md, "", "csd04", f)
    return [x["message"] for x in f.items if x["check"] == "content-labels"]


def doc(title, first_para):
    return f"# 1 Introduction\n\nText.\n\n# {title}\n\n{first_para}\n\nMore text.\n"


TEMPLATE_APPENDIX = ("(This appendix does not form an integral part of this specification "
                     "and is informational.)")


# The exact CSD04 headings and first paragraphs.
@pytest.mark.parametrize("title, first_para", [
    ("Appendix A. Acknowledgments<a id='acknowledgments'></a>", TEMPLATE_APPENDIX),
    ("Appendix B. Revision History<a id='revision-history'></a>", TEMPLATE_APPENDIX),
    ("Appendix C. Guidance on the Size of CSAF Documents<a id='guidance-on-the-size-of-csaf-documents'></a>",
     "This appendix provides informative guidance on the size of CSAF documents."),
    ("Appendix D. Collapsing Product Paths<a id='collapsing-product-paths'></a>", TEMPLATE_APPENDIX),
])
def test_csaf_csd04_appendices_are_labelled(title, first_para):
    assert findings(doc(title, first_para)) == []


@pytest.mark.parametrize("first_para", [
    "(This annex forms an integral part of this Specification.)",
    "(This appendix does not form an integral part of this Specification and is informational.)",
    "(This appendix does not form an integral part of this Recommendation.)",
    "This annex is informational.",
    "This appendix contains non-normative material on deployment.",
    "This appendix gives informative guidance.",
])
def test_template_and_plain_status_sentences_are_labels(first_para):
    assert findings(doc("Annex B References", first_para)) == []


@pytest.mark.parametrize("first_para", [
    "This appendix provides guidance on the size of documents.",
    "The following individuals were members of the TC.",
    "This appendix provides guidance; informative material follows later.",
    "(See the integral part of this specification in section 3.)",
])
def test_an_unlabelled_appendix_is_still_reported(first_para):
    msgs = findings(doc("Appendix C Guidance", first_para))
    assert len(msgs) == 1 and "Appendix C Guidance" in msgs[0]


def test_the_advisory_names_the_template_sentence_and_does_not_demand_one_word():
    msgs = findings(doc("Appendix C Guidance", "Some guidance."))
    assert len(msgs) == 1
    assert "does not form an integral part" in msgs[0]
    assert "label it 'Non-normative'" not in msgs[0]
    # 'Non-normative' was our advice, not an OASIS rule: the template's
    # sentence is the label the template requires (CSAF csd04 review).
    assert "Non-normative" not in msgs[0]
