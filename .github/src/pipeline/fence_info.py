# Copyright 2026 OASIS Open
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Authored by Michael Coletta, Technical Advisor to OASIS Open.

"""Read a code fence's info string the way GitHub does, before pandoc.

An opening fence written as a language name followed by more text,

    ```yaml <!--json-path($.properties)-->

is a code block on GitHub and under pandoc's gfm and commonmark readers,
which take the first word as the language and ignore the rest. pandoc's
markdown reader, the one step 1 converts with, does not recognise the line as
a fence and collapses the block to inline code. CSAF v2.1 csd04 carries 96
such fences; GitHub and the TC's own HTML show all of them as code.

publisher-toolkit's step 1 rewrites these openings before pandoc
(lib/preprocess_md.py, v0.2.0, May 2026). This module gives this repository's
step 1 (pipeline.html_converter) and verify/verify_md.py the same reading:
the language name stays, the rest of the info string is dropped, exactly as
GitHub renders it. Fence bodies, closing fences, curly-attribute openings
(```{.yaml}) and bare openings are left alone.

Standard library only: verify_md.py loads this file by path, without the
pipeline package and its third-party imports.
"""

from __future__ import annotations

import contextlib
import os
import re
import tempfile
from typing import Iterator

# An opening or closing fence: up to three spaces, then three or more
# backticks or tildes (CommonMark 4.5).
_FENCE = re.compile(r"^(?P<indent> {0,3})(?P<delim>`{3,}|~{3,})(?P<info>.*)$")
# A language name followed by whitespace and more text. The language grammar
# is publisher-toolkit's (LANG_TOKEN_RE_SRC), so the two step 1s agree.
_LANG_AND_MORE = re.compile(r"^\s*(?P<lang>[A-Za-z][A-Za-z0-9_+.#-]*)\s+\S")


def bare_fence_info(md: str) -> tuple[str, list[int]]:
    """Return ``md`` with each opening fence's info string cut to its
    language name where more text follows it, and the 1-based line numbers
    changed. Line endings are kept as they were."""
    out: list[str] = []
    changed: list[int] = []
    open_delim = ""
    for n, raw in enumerate(md.splitlines(keepends=True), 1):
        body = raw.rstrip("\r\n")
        ending = raw[len(body):]
        m = _FENCE.match(body)
        if not m:
            out.append(raw)
            continue
        delim, info = m.group("delim"), m.group("info")
        if open_delim:
            if delim[0] == open_delim[0] and len(delim) >= len(open_delim) and not info.strip():
                open_delim = ""
            out.append(raw)
            continue
        if delim[0] == "`" and "`" in info:
            out.append(raw)          # CommonMark: not a fence at all
            continue
        open_delim = delim
        lm = _LANG_AND_MORE.match(info)
        if lm and not info.lstrip().startswith("{"):
            out.append(f"{m.group('indent')}{delim}{lm.group('lang')}{ending}")
            changed.append(n)
        else:
            out.append(raw)
    return "".join(out), changed


@contextlib.contextmanager
def pandoc_input(md_path: str) -> Iterator[tuple[str, list[int]]]:
    """Yield the path pandoc should read and the lines rewritten. When nothing
    needs rewriting this is ``md_path`` itself; otherwise a temporary copy in
    the same directory (so relative image and include paths still resolve),
    removed on exit."""
    with open(md_path, encoding="utf-8", newline="") as fh:
        text, changed = bare_fence_info(fh.read())
    if not changed:
        yield md_path, changed
        return
    fd, tmp = tempfile.mkstemp(prefix=".fence_info_", suffix=".md",
                               dir=os.path.dirname(os.path.abspath(md_path)))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
        yield tmp, changed
    finally:
        with contextlib.suppress(OSError):
            os.remove(tmp)
