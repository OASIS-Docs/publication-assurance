"""The PDF preprocessor must let inline code wrap.

With white-space: nowrap, one long inline path (DMLex v1.0 s3.2.1, 1118px on
a 643px line) widened the page and Chrome scaled every page of the 140-page
PDF to 62%, so 12pt body text printed at about 7.5pt.
"""

from __future__ import annotations

import re

from conftest import REPO_ROOT

# Read the stylesheet from source: importing the pipeline pulls in
# BeautifulSoup, which the gate's test environment does not install.
SOURCE = (REPO_ROOT / ".github/src/pipeline/pdf_preprocessor.py").read_text()


def css():
    return SOURCE


def rule(selector):
    m = re.search(r"(?m)^\s*" + re.escape(selector) + r"\s*\{(.*?)\}", css(), re.S)
    assert m, f"no CSS rule for {selector!r}"
    return m.group(1)


def test_inline_code_can_wrap():
    body = rule("code")
    assert "nowrap" not in body, body
    assert "overflow-wrap: anywhere" in body, body


def test_code_in_tables_can_wrap():
    body = rule("table code, td code, th code")
    assert "nowrap" not in body, body
