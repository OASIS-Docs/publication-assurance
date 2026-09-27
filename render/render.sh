#!/usr/bin/env bash
# Copyright 2026 OASIS Open
# SPDX-License-Identifier: Apache-2.0
# Authored by Michael Coletta, Technical Advisor to OASIS Open.
#
# Render one OASIS Markdown specification through this repository's pipeline,
# stage it where it would sit on docs.oasis-open.org, and run the gate on it.
#
#   render/render.sh MD_DIR SCHEMAS_DIR OUT_ROOT
#
# MD_DIR       the directory holding the .md and the figures it references
# SCHEMAS_DIR  the schemas it cites, staged as <stage>/schemas; "-" for none
# OUT_ROOT     receives the staged tree, e.g. OUT_ROOT/lexidma/dmlex/v1.0/os/
#
# The stage path comes from the "This stage" URL in the Markdown, so the
# directory, the file names and the cover are the ones the gate checks
# against each other. Markdown to HTML is the pipeline's step 1 and the PDF
# preprocessor is step 2's (type scale, code wrapping); the PDF itself is
# printed by headless Chrome through print_pdf.mjs, with the footer read from
# the document by footer.py (see print_pdf.mjs for why not wkhtmltopdf).
#
# Exit status is the gate's: 0 publishable, 1 blockers. PUBCHECK=0 stops
# after staging (CI then runs the gate through the published action).
# Needs pandoc 3.x, python3 with beautifulsoup4, poppler (pdfinfo), Node.js 18 or later
# (puppeteer-core is installed next to this script on first run) and Chrome or
# Chromium (CHROME overrides discovery).
set -euo pipefail
case "${1:-}" in -h|--help|"") sed -n '5,28p' "$0" | sed 's/^# \{0,1\}//'; exit 0;; esac
HERE=$(cd "$(dirname "$0")" && pwd)
PA=$(cd "$HERE/.." && pwd)
MD_DIR=$(cd "$1" && pwd)
SCHEMAS=${2:--}
[ "$SCHEMAS" = - ] || SCHEMAS=$(cd "$SCHEMAS" && pwd)
mkdir -p "$3"; OUT=$(cd "$3" && pwd)

MDS=$(ls "$MD_DIR"/*.md | grep -v "/README.md$" || true)
[ "$(printf '%s\n' "$MDS" | grep -c .)" = 1 ] || { echo "MD_DIR must hold exactly one specification .md: $MDS" >&2; exit 2; }
MD=$MDS
NAME=$(basename "$MD" .md)
# The stage path, and the footer, come from the document (footer.py).
FOOTER=$(mktemp); trap 'rm -f "$FOOTER"' EXIT
python3 "$HERE/footer.py" "$MD" > "$FOOTER" || exit 2
REL=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["path"])' "$FOOTER")
STAGE="$OUT/$REL"
echo "Staging $NAME at $REL"

# 1. Stage the source, the figures it references and the schemas.
mkdir -p "$STAGE"
rsync -a --delete --exclude '*-verification.json' --exclude README.md --exclude schemas "$MD_DIR"/ "$STAGE"/
[ "$SCHEMAS" = - ] || rsync -a "$SCHEMAS"/ "$STAGE/schemas/"

# 2. Markdown to HTML: the pipeline's step 1 (pandoc, the OASIS stylesheet,
#    the post-processor). OUT is the repo base, so the converter resolves the
#    document's own publish URL.
( cd "$STAGE" && python3 "$PA/.github/src/step_1_markdown_to_html_converter_V3_0.py" \
    "$STAGE/$NAME.md" "$OUT" "$STAGE" --md-to-html > "$OUT/stage1.log" 2>&1 ) || {
  cat "$OUT/stage1.log" >&2; echo "Step 1 (Markdown to HTML) failed" >&2; exit 1; }
rm -f "$STAGE/markdown_conversion.log"
rmdir "$STAGE/images" 2>/dev/null || true
test -s "$STAGE/$NAME.html"

# 3. HTML to PDF: step 2's preprocessor, then Chrome.
python3 "$PA/.github/src/fix_html_for_pdf.py" "$STAGE/$NAME.html" -o "$STAGE/.$NAME-pdf.html" > "$OUT/stage2.log" 2>&1
if [ -z "${CHROME:-}" ]; then
  for c in google-chrome chromium chromium-browser "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"; do
    command -v "$c" >/dev/null 2>&1 && CHROME=$c && break
  done
fi
CHROME=$(command -v "${CHROME:-}" || echo "${CHROME:-}")
[ -x "$CHROME" ] || { echo "no Chrome or Chromium found; set CHROME" >&2; exit 2; }
export CHROME
[ -d "$HERE/node_modules/puppeteer-core" ] || npm install --prefix "$HERE" --no-save --silent puppeteer-core@24
node "$HERE/print_pdf.mjs" "$STAGE/.$NAME-pdf.html" "$STAGE/$NAME.pdf" "$FOOTER"
# The contents' page numbers come from the printed PDF; print a numbered
# copy until no number moves (numbering can push a heading onto the next page).
for pass in 1 2 3 4; do
  CHANGED=$(python3 "$PA/.github/src/pipeline/toc_pages.py" "$STAGE/.$NAME-pdf.html" "$STAGE/$NAME.pdf" "$STAGE/.$NAME-pdf-numbered.html" | tee /dev/stderr | sed -n 's/.*, \([0-9]*\) changed$/\1/p')
  [ "$CHANGED" = 0 ] && break
  if [ "$pass" = 4 ]; then
    # never ship numbers that were not checked: print the unnumbered HTML
    echo "contents page numbers did not settle after 4 passes; left unnumbered" >&2
    node "$HERE/print_pdf.mjs" "$STAGE/.$NAME-pdf.html" "$STAGE/$NAME.pdf" "$FOOTER"
    break
  fi
  node "$HERE/print_pdf.mjs" "$STAGE/.$NAME-pdf-numbered.html" "$STAGE/$NAME.pdf" "$FOOTER"
done
rm -f "$STAGE/.$NAME-pdf.html" "$STAGE/.$NAME-pdf-numbered.html"
test -s "$STAGE/$NAME.pdf"

# 4. The gate. Exit 0 means publishable; warnings do not fail.
echo "Staged: $STAGE"
[ "${PUBCHECK:-1}" = 0 ] && exit 0
python3 "$PA/pub-check/oasis_pub_check.py" "$STAGE"
