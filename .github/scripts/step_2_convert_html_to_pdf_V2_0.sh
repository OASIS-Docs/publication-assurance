#!/bin/bash
# Copyright 2025-2026 OASIS Open
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

# Stage 2 as TRANSFORMS.md documents it: the PDF preprocessor, then the
# renderer's A4 argument vector (PdfRenderer.build_command). The preprocessed
# copy sits beside the source so relative CSS and images resolve, is hidden
# (a leading dot) so no later `*.html` search can pick it, and is removed on
# exit. The footer carries the published HTML's name, not the copy's. The
# Python steps run in a scratch directory so their log files never land in
# the package. PYTHON selects the interpreter (the workflow passes its venv's).
set -euo pipefail

DIR="${1:-}"
if [ -z "$DIR" ] || [ ! -d "$DIR" ]; then
  echo "Directory not specified or does not exist: $DIR"
  exit 1
fi

HTML_FILE=$(find "$DIR" -maxdepth 1 -name '*.html' ! -name '.*' ! -name '*_fixed.html' | sort | head -n 1)
if [ -z "$HTML_FILE" ]; then
  echo "HTML file not found in directory: $DIR"
  exit 1
fi
HTML_FILE=$(cd "$(dirname "$HTML_FILE")" && pwd)/$(basename "$HTML_FILE")
NAME=$(basename "$HTML_FILE" .html)
PDF_FILE="$(dirname "$HTML_FILE")/$NAME.pdf"
TMP_HTML="$(dirname "$HTML_FILE")/.$NAME-pdf.html"
SRC=$(cd "$(dirname "$0")/../src" && pwd)
PY=${PYTHON:-python3}
WORK=$(mktemp -d)
trap 'rm -rf "$TMP_HTML" "$WORK"' EXIT

echo "Found HTML file: $HTML_FILE"
echo "Output PDF file will be: $PDF_FILE"
( cd "$WORK" && "$PY" "$SRC/fix_html_for_pdf.py" "$HTML_FILE" -o "$TMP_HTML" )
( cd "$WORK" && "$PY" "$SRC/step_2_convert_html_to_pdf.py" "$TMP_HTML" -o "$PDF_FILE" \
    --footer-name "$(basename "$HTML_FILE")" )
test -s "$PDF_FILE"
echo "HTML to PDF conversion completed successfully"
