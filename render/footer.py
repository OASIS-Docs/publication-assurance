#!/usr/bin/env python3
# Copyright 2026 OASIS Open
# SPDX-License-Identifier: Apache-2.0
# Authored by Michael Coletta, Technical Advisor to OASIS Open.
"""The PDF footer of an OASIS Markdown specification, read from the document.

Published OASIS PDFs carry the document name, its track ("Standards Track
Work Product", or "Non-Standards Track Work Product" for a Committee Note or
a Project Note), the copyright line and the document date on every page.
Every value comes from the Markdown itself, never from the render: the name
is the file's stem, the stage is read from its "This stage" URL, the date
from its date line and the copyright line from its Notices.

Usage: footer.py SPEC.md   (prints JSON: name, stage, path, track, copyright, date)
"path" is the document's directory under docs.oasis-open.org, which
render.sh stages it at.
Exit 2 when the document does not say what the footer needs.
"""
import html
import json
import re
import sys
from pathlib import Path

# Committee Notes and Project Notes, with the retired Committee Note stages
# older documents still carry (Naming Directives v1.7 retired cnprd).
NON_STANDARDS_TRACK = ('cnd', 'cn', 'cnprd', 'pnd', 'pn')


def footer(md_path):
    md = Path(md_path)
    text = html.unescape(md.read_text(encoding='utf-8'))
    text = re.sub(r'```.*?```', '', text, flags=re.S)  # a code sample is not the document's notice
    name = md.stem
    missing = []
    stage_url = re.search(r'https?://docs\.oasis-open\.org/([^\s()\[\]<>]*?/([a-z]+)\d*)/' + re.escape(name) + r'\.html', text)
    date = re.search(r'^## (\d{1,2} [A-Z][a-z]+ \d{4})\s*$', text, re.M)
    notice = re.search(r'Copyright (?:©|\(c\)) OASIS Open (\d{4}(?:[-\u2013]\d{4})?)\.', text, re.I)
    if not stage_url:
        missing.append(f'a docs.oasis-open.org URL ending /{name}.html (the This stage URL)')
    if not date:
        missing.append('a date line such as "## 29 April 2025"')
    if not notice:
        missing.append('a line "Copyright © OASIS Open YYYY."')
    if missing:
        raise ValueError(f'{md}: no ' + '; no '.join(missing))
    stage = stage_url.group(2)
    track = 'Non-Standards Track Work Product' if stage in NON_STANDARDS_TRACK else 'Standards Track Work Product'
    copyright_line = f'Copyright © OASIS Open {notice.group(1)}. All Rights Reserved.'
    return {'name': name, 'stage': stage, 'path': stage_url.group(1), 'track': track,
            'copyright': copyright_line, 'date': date.group(1)}


if __name__ == '__main__':
    try:
        print(json.dumps(footer(sys.argv[1]), ensure_ascii=False))
    except (ValueError, OSError, IndexError) as e:
        print(f'footer.py: {e}', file=sys.stderr)
        sys.exit(2)
