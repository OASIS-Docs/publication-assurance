# Copyright 2026 OASIS Open
# SPDX-License-Identifier: Apache-2.0
# Authored by Michael Coletta, Technical Advisor to OASIS Open.
"""Plain-English explanation of every check class, for the people who edit the document.

One entry per check class that `oasis_pub_check.py --list-checks` reports, keyed
by the class id. Each entry says, in words an editor uses rather than the
checker's own terms, what is wrong with the document and what to change in it.
The finding's own message travels beside this text as the exact detail, so the
explanation here can stay general to the class.

tests/test_tc_view.py fails if a check class has no entry here, or if an entry
names a class the checker does not have, so a new check cannot ship without
its explanation.
"""
from __future__ import annotations

# check class -> (what is wrong, how to fix it)
PLAIN: dict[str, tuple[str, str]] = {
    "artifact-naming": (
        "A supporting file's name does not say which draft it belongs to.",
        "Rename the file so its name carries the same draft label as the document "
        "(for example -csd01), or confirm it is meant to keep the same name in every draft."),
    "asset-refs": (
        "The HTML refers to a file (an image, stylesheet or script) that is not in the package.",
        "Add the missing file to the package at the path the HTML uses, or correct the path in the document."),
    "authors": (
        "The cover page does not name the authors, or the Authors section is empty or still a placeholder.",
        "Add an Authors section on the cover page and list the authors by name."),
    "boilerplate-dup": (
        "The paragraph that tells readers how to send comments appears more than once.",
        "Keep one copy of the 'send comments' paragraph in the Status section and delete the others."),
    "case": (
        "A file name, or a link to this document on docs.oasis-open.org, contains capital letters.",
        "Use lower case for every file name in the package and for every docs.oasis-open.org address "
        "that points at this document."),
    "comment-resolution-log": (
        "The comment resolution log is missing or does not have the required file name.",
        "Name the log exactly as the naming rules require (the document's file name followed by "
        "-comment-resolution-log) and include it in the package."),
    "conformance-structure": (
        "The Conformance section is not where it should be, or its numbered clauses are missing, "
        "repeated, or changed since the previous draft.",
        "Make Conformance a top-level numbered section, give each clause a unique number, and keep "
        "the clause numbers from the previous draft (add new clauses at the end rather than renumbering)."),
    "content-labels": (
        "An Examples section does not say whether it is normative or non-normative.",
        "Add '(Non-normative)' to the heading, or open the section with a sentence saying the "
        "examples are non-normative."),
    "cover-hr": (
        "There is a horizontal line between the OASIS logo and the title on the cover page.",
        "Delete the horizontal line (--- in Markdown, <hr> in HTML) between the logo and the title."),
    "date-sync": (
        "The date of the document does not match between its formats, or the copyright year does "
        "not match the document date.",
        "Use the same date in the Markdown, the HTML and the PDF, and make the copyright year the "
        "year of that date."),
    "dead-lists": (
        "The document gives an email address or archive link on lists.oasis-open.org, which no longer works.",
        "Remove the lists.oasis-open.org address and point readers to the committee's current "
        "comment page or email address instead."),
    "double-slash": (
        "A link path contains a double slash (//) where a single slash was meant.",
        "Remove the extra slash from the link."),
    "extension-conformance": (
        "A file in the package has an unusual file extension for a published document.",
        "Use a standard extension (.md, .html, .pdf, .docx, .odt, .zip and similar), or confirm "
        "the extension is intentional."),
    "extension-count": (
        "A file name has no extension, or more than one, where exactly one is expected.",
        "Rename the file so it ends with a single extension such as .html or .pdf."),
    "fence-collapse": (
        "A code block's opening line has extra text after the language name, so the block may "
        "appear as one line of inline code.",
        "Put only the language name after the opening ``` (for example ```json), and move any "
        "title into the text above the block."),
    "filenames": (
        "The document's files are missing, not all named alike, or named with a working label "
        "instead of the draft label.",
        "Give every format of the document the same name ending in the draft label (for example "
        "name-v1.0-csd01.md, .html and .pdf), and include the Markdown, HTML and PDF."),
    "front-matter": (
        "The 'This version' or 'Latest version' links on the cover page are missing, point at the "
        "wrong place, or name a file that is not in the package.",
        "Correct the cover-page links so 'This version' lists the .md, .html and .pdf of this draft "
        "at their docs.oasis-open.org addresses, and 'Latest version' points at the version folder "
        "without a draft label. Each link should be a plain address with nothing after it."),
    "generator": (
        "The PDF of a Word-authored document was not produced by Microsoft Word.",
        "Save the PDF from Microsoft Word so it matches the Word source."),
    "html-anchors": (
        "A link inside the document points at a section that does not exist, or the HTML has no "
        "linked table of contents.",
        "Correct the link so it matches a heading's anchor (it starts with #), and include a "
        "linked table of contents."),
    "html-code-sync": (
        "A code block in the HTML is different from the same block in the Markdown.",
        "Rebuild the HTML from the current Markdown so the code blocks match exactly."),
    "html-residue": (
        "The HTML contains leftovers from the conversion: a duplicate title, a build-machine path, "
        "or formatting codes shown as text.",
        "Remove the leftover text from the source and rebuild the HTML so the title appears once "
        "and no build paths or {#...} codes are visible."),
    "html-title": (
        "The HTML page title (shown in the browser tab) is missing, a placeholder, or not the "
        "document's title.",
        "Set the HTML <title> to the document's full title."),
    "image-policy": (
        "An image is missing, too large, too wide for the page, or written in a way the published "
        "page cannot show safely.",
        "Use a plain image with a relative path that is in the package, keep each image small "
        "enough and no wider than the page, and remove any script or external link from SVG files."),
    "junk-files": (
        "The package contains working folders or system files (such as .DS_Store or backup files).",
        "Delete the working folders and system files from the package."),
    "link-mismatch": (
        "A link shows one web address as its text but goes to a different address.",
        "Make the link text and the link destination the same address."),
    "logo": (
        "The logo on the cover page is not the standard OASIS logo.",
        "Use the standard OASIS logo from the document template."),
    "manifest": (
        "The package's manifest file is unreadable, lists a file that is missing, or records a "
        "checksum that does not match.",
        "Regenerate the manifest after the last change to the package's files."),
    "md-links": (
        "A link in the Markdown is written in a way that displays badly in the HTML or PDF.",
        "Write a web address on its own as <https://...>, or give the link real text, as in "
        "[link text](https://...). Put a space after an address that ends a sentence."),
    "member-uri": (
        "The document links to a members-only OASIS page that the public cannot open.",
        "Replace the link with a public page, or remove it."),
    "multi-part-naming": (
        "The files of a multi-part document are not named consistently.",
        "Name every part file the same way: the document name, then -partN-<name>, numbered from "
        "1 with no gaps, using the same name for a part in every format."),
    "name-chars": (
        "A file or folder name contains a character that is not allowed.",
        "Use only lower-case letters, digits, hyphens and full stops in the names of the document's "
        "files and folders."),
    "normdef-refs": (
        "A schema or other definition file in the package is not mentioned in the document.",
        "Refer to the file from the document (usually in the Conformance section or an annex), or "
        "remove it from the package."),
    "ns-segment": (
        "A cover-page link uses the /ns/ path, which is reserved for namespaces.",
        "Change the cover-page link to the document's own address, without /ns/."),
    "odt-integrity": (
        "The OpenDocument (.odt) file is damaged or contains macros.",
        "Save the document again from the word processor as a plain .odt file without macros."),
    "package-refs": (
        "The document refers to a file in this draft's folder that is not in the package.",
        "Add the referenced file to the package, or correct the reference."),
    "pdf-cover": (
        "The PDF cover page shows the title more than once, or the PDF contains a build-machine path.",
        "Remove the duplicate title from the source, rebuild the PDF, and check the cover page shows "
        "the title once."),
    "pdf-fonts": (
        "The PDF uses fonts that the document's stylesheet does not ask for.",
        "Build the PDF from the document's own HTML and stylesheet, or confirm the different fonts "
        "are intended."),
    "pdf-legibility": (
        "Text in the PDF is printed noticeably smaller than the document's normal body text.",
        "Make the small text (often code or tables) larger in the stylesheet, or reduce what has "
        "to fit on the line, and rebuild the PDF."),
    "pdf-sync": (
        "The PDF could not be read, or it does not give this draft's 'This version' address, or it "
        "cites another version unexpectedly.",
        "Rebuild the PDF from the current HTML so it carries the same cover-page links."),
    "pdf-toc-pages": (
        "The PDF table of contents has no page numbers, or a page number is wrong.",
        "Rebuild the PDF so the table of contents shows the page on which each section starts."),
    "previous-stage": (
        "The cover page does not give a 'Previous version' link, which every draft after the first needs.",
        "Add a 'Previous version' entry to the cover page linking to the previous draft."),
    "public-review-metadata": (
        "The public review metadata file is missing, empty or cannot be opened.",
        "Include the public review metadata file for this draft in the package."),
    "ref-rfc": (
        "An RFC reference's label, link and text name different RFC numbers.",
        "Make the label, the link and the citation text of the reference name the same RFC."),
    "references-split": (
        "The References section is not divided into Normative and Informative references, or one "
        "reference appears under both.",
        "Split References into 'Normative References' and 'Informative References', and list each "
        "reference only once."),
    "residue": (
        "The document still contains editor notes, 'TBD' placeholders or template instructions.",
        "Replace each TODO, TBD or template instruction with the final text, or delete it."),
    "revision-collision": (
        "A draft with this label is already published on docs.oasis-open.org.",
        "Use the next draft number (for example csd02 instead of csd01) for this publication."),
    "rfc-keywords": (
        "The document uses words such as MUST and SHOULD without citing RFC 2119 and RFC 8174.",
        "Add RFC 2119 and RFC 8174 to the Normative References and cite them where the key words "
        "are introduced."),
    "schema-id": (
        "A JSON file cannot be read, or a schema's $id does not match the address where it will be "
        "published.",
        "Fix the JSON syntax, and set each schema's $id (and references inside it) to its "
        "docs.oasis-open.org address."),
    "stage-name": (
        "The draft's folder name is not a current draft label with a two-digit number (for example csd01).",
        "Rename the folder to a current label: csd01, cs01, cnd01, cn01 or os, with a two-digit number."),
    "stage-token": (
        "A cover-page link names a draft label that does not fit this document.",
        "Correct the 'Previous version' and 'Latest version' links: Previous names the earlier "
        "draft's label, and Latest has no draft label at all."),
    "stage-uri-live": (
        "A 'Previous version' or 'Latest version' link on the cover page does not open.",
        "Correct the link so it opens the published page."),
    "symlinks": (
        "The package contains a shortcut (symbolic link) that points back to itself or a parent folder.",
        "Remove the symbolic link from the package."),
    "template": (
        "A required section of the document template is missing or out of order.",
        "Add the missing section from the OASIS template (including Conformance) and keep the "
        "template's order."),
    "template-css": (
        "The HTML has no stylesheet, or uses one with different fonts from the OASIS template.",
        "Use the OASIS template stylesheet, or keep its fonts if you use your own."),
    "title-oasis-prefix": (
        "The document title starts with the word 'OASIS'.",
        "Remove 'OASIS' from the start of the title."),
    "title-version": (
        "The title on the cover page does not carry the document's version, or carries a different one.",
        "Write the title as '<Name> Version <number>', with the same version as the folder and file names."),
    "uri-alias": (
        "The package has a redirecting page, two identical copies of a file, or a link through a "
        "link-shortening or redirect service.",
        "Remove redirect pages and duplicate copies, and link directly to the final address."),
    "uri-chars": (
        "A 'This version' or 'Latest version' address contains an underscore.",
        "Use hyphens instead of underscores in the document's addresses and file names."),
    "version-naming": (
        "The version folder or the version in the file names is not written as v1.0 (or v1.0.1), "
        "or the two disagree.",
        "Name the version folder like v1.0, and use the same version in every file name."),
    "vml-fallback": (
        "An image drawn in Word's old VML format has no ordinary image to fall back on.",
        "Insert the image again as a normal picture, or save the HTML with picture fallbacks."),
    "xml-namespace": (
        "An XML namespace in the package does not follow the OASIS namespace pattern, or is "
        "declared in conflicting ways.",
        "Use namespaces of the form https://docs.oasis-open.org/<committee>/ns/<name>, and declare "
        "each one the same way everywhere."),
}

# Where one condition of a class would be misdescribed by the class's text,
# its own text, keyed by (check class, the condition's registered signature,
# severity). A finding takes this text when its class and severity match and
# its message contains the signature. The test pins every key to a condition
# the checker registers, so a reworded message cannot leave a stale entry.
CONDITIONS: dict[tuple[str, str, str], tuple[str, str]] = {
    ("front-matter", "confirm this is an intentional external reference", "WARN"): (
        "The document links to a different version of this specification on docs.oasis-open.org.",
        "Check that the link is meant to point at that other version (for example a reference to "
        "an earlier version); if not, change it to this version's address."),
    ("dead-lists", "archives", "WARN"): (
        "The document links into the old mailing list archive on lists.oasis-open.org.",
        "Open each archive link and check it still works; replace any that do not, or remove them."),
    ("filenames", "No authoritative source artifact", "WARN"): (
        "The package has the HTML and PDF but not the source file they were made from.",
        "Include the source (the Markdown, Word or OpenDocument file) in the package."),
    ("stage-name", "is a Working Draft. Working Drafts are unpublished", "WARN"): (
        "This folder is a Working Draft, and Working Drafts are not published.",
        "Before submitting, rename the folder to the label it will be published under (for "
        "example csd01)."),
    ("residue", "'Will be filled in", "WARN"): (
        "A 'Will be filled in' placeholder is still in the document.",
        "This is fine for an early draft. Replace it with the final text before the document "
        "becomes a Committee Specification."),
    ("pdf-sync", "pdftotext not on PATH", "WARN"): (
        "The PDF could not be compared with the HTML on this machine.",
        "Nothing to change in the document. Compare the PDF's cover page with the HTML by eye."),
    ("pdf-sync", "pdftotext failed", "WARN"): (
        "The PDF's text could not be read.",
        "Rebuild the PDF, and check it opens and that its text can be selected and copied."),
    ("pdf-fonts", "pdffonts failed", "WARN"): (
        "The fonts in the PDF could not be read.",
        "Rebuild the PDF, and check it opens in a PDF reader."),
    ("pdf-legibility", "pdftotext -bbox failed", "WARN"): (
        "The size of the text in the PDF could not be measured.",
        "Rebuild the PDF, and check it opens and that its text can be selected and copied."),
    ("schema-id", "not valid JSON (", "BLOCKER"): (
        "A JSON file in the package is not valid JSON.",
        "Correct the JSON syntax at the place the detail names."),
    ("schema-id", "An implementer following the $id", "BLOCKER"): (
        "A schema's $id is not the address the file will be published at.",
        "Set the schema's $id to the file's address on docs.oasis-open.org (the detail gives "
        "the folder it publishes under), or move the file so it publishes at its $id."),
    ("schema-id", "disagrees with $id", "BLOCKER"): (
        "A reference inside a schema does not match the schema's own $id.",
        "Make the schema's references to itself use the same address as its $id."),
    ("conformance-structure", "Stability not verified - previous stage unavailable", "WARN"): (
        "The previous draft could not be fetched, so its Conformance clauses were not compared "
        "with this one.",
        "Nothing to change in the document. Check by hand that no clause from the previous "
        "draft was removed or renumbered."),
}

# A finding from a class this table does not know (it cannot happen while the
# test above holds, but a report must never fail for want of a sentence).
FALLBACK = ("The checks found a problem with the document.",
            "Read the detail and correct the document as it describes.")


# A check that could not run says so ("NOT EVALUATED: ..."), whatever its
# class: the class text would describe a defect nobody has found.
NOT_EVALUATED = (
    "This check could not run, because the cover page does not give this draft's own "
    "'This version' address.",
    "Add the 'This version' links (the .md, .html and .pdf at their docs.oasis-open.org "
    "addresses) to the cover page, then run the checks again so this one can run.")
NOT_EVALUATED_OTHER = (
    "This check could not run, so the document has not been checked for it yet.",
    "The detail says what the check needed. Once that is in place, run the checks again.")


def explain(check: str, message: str = "", severity: str = "") -> tuple[str, str]:
    """(what is wrong, how to fix it) for one finding: its condition's own
    text where it has one, else its check class's."""
    if message.startswith("NOT EVALUATED"):
        return NOT_EVALUATED if "gave no base URL" in message else NOT_EVALUATED_OTHER
    for (c, sig, sev), text in CONDITIONS.items():
        if c == check and sev == severity and sig in message:
            return text
    return PLAIN.get(check, FALLBACK)
