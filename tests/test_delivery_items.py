"""Regression fixtures for find_delivery_items (fixed in 14ad114).

The delivery item per format is the file whose stem ends in -<stage>; when no
file matches, the scan falls back to the SHORTEST stem so the filename check
can still report a pre-rename package. `index.html` is shorter than any
conforming spec filename, and every DEPLOYED OASIS tree carries a generated
index.html per directory, so the fallback used to select the directory listing
as the delivery HTML. The cover, front-matter, title-version and asset-ref
checks then graded a directory listing instead of the specification.

Audit-only mode is the worst affected, because it points at a deployed tree by
definition.
"""

from __future__ import annotations

import shutil

import pytest

from conftest import CORPUS, FIXTURES, oasis_pub_check, run_cli, stage_from_corpus

find_delivery_items = oasis_pub_check.find_delivery_items

CSAF_CSD01 = CORPUS / "csaf" / "v2.1" / "csd01"


def _basename(items: dict, ext: str) -> str:
    from pathlib import Path
    return Path(items[ext]).name if ext in items else "(none)"


def test_index_html_is_never_selected_as_the_delivery_item(tmp_path):
    """A deployed tree whose spec HTML lacks the -<stage> suffix: the shortest
    stem is index.html, and it must still lose to the specification."""
    stage = stage_from_corpus(tmp_path, CSAF_CSD01,
                              rename_stem="csaf-v2.1", with_index=True)
    assert (stage / "index.html").exists(), "fixture must carry the directory listing"

    items = find_delivery_items(str(stage))

    assert _basename(items, "html") == "csaf-v2.1.html", (
        "the generated directory listing displaced the specification as the "
        f"delivery HTML: got {_basename(items, 'html')}"
    )


def test_conforming_stage_suffixed_html_still_wins_over_index_html(tmp_path):
    """The exact -<stage> branch already beat index.html. Skipping the listing
    must not disturb that path."""
    stage = stage_from_corpus(tmp_path, CSAF_CSD01, with_index=True)

    items = find_delivery_items(str(stage))

    assert _basename(items, "html") == "csaf-v2.1-csd01.html", (
        "the conforming -<stage> delivery HTML was displaced: "
        f"got {_basename(items, 'html')}"
    )


def test_index_html_is_skipped_case_insensitively(tmp_path):
    """A tree served from a case-insensitive filesystem can carry Index.html."""
    stage = stage_from_corpus(tmp_path, CSAF_CSD01, rename_stem="csaf-v2.1")
    (stage / "INDEX.HTML").write_text("<html><title>Index of /</title></html>",
                                      encoding="utf-8")

    items = find_delivery_items(str(stage))

    assert _basename(items, "html") == "csaf-v2.1.html", (
        "an upper-cased directory listing was selected as the delivery HTML: "
        f"got {_basename(items, 'html')}"
    )


def test_a_directory_listing_does_not_suppress_cover_blockers():
    """The dangerous direction. Member-only Kavi URIs live only on the real
    cover; the directory listing has none, so grading the listing silently
    passed a package that must not publish."""
    stage = FIXTURES / "cover_only_defect" / "v2.5" / "os"
    result = run_cli(str(stage))

    member_uri = [line for line in result.stdout.splitlines()
                  if "member-uri" in line and "BLOCKER" in line]

    assert len(member_uri) == 2, (
        "the cover's OASIS member-only (Kavi) URIs were not reported; the "
        "check ran against the directory listing instead of the cover. "
        f"stdout:\n{result.stdout}"
    )


def test_the_directory_listing_is_reported_as_an_auxiliary_file():
    """index.html is server-only by the publication contract: not a delivery
    item, but still a file present in the package."""
    stage = FIXTURES / "cover_only_defect" / "v2.5" / "os"
    items = find_delivery_items(str(stage))

    aux = oasis_pub_check.auxiliary_files(str(stage), items)

    assert "index.html" in aux, (
        f"index.html vanished from the package inventory entirely: {aux}"
    )


def test_delivery_items_share_one_basename_on_a_deployed_tree(tmp_path):
    """The `filenames` check compares the stems of the delivery items. With
    index.html selected they could never agree, so every deployed tree drew a
    spurious 'Delivery items do not share one basename' blocker."""
    stage = stage_from_corpus(tmp_path, CSAF_CSD01,
                              rename_stem="csaf-v2.1", with_index=True)
    result = run_cli(str(stage))

    spurious = [line for line in result.stdout.splitlines()
                if "do not share one basename" in line]

    assert not spurious, (
        "the directory listing was counted among the delivery items: "
        f"{spurious}"
    )
