#!/usr/bin/env bash
# Copyright 2026 OASIS Open
# SPDX-License-Identifier: Apache-2.0
# Authored by Michael Coletta, Technical Advisor to OASIS Open.
#
# Convert an OASIS DocBook specification to Markdown and verify it.
#
#   build.sh --profile NAME|DIR SPEC_DIR OUT_DIR [PUBLISHED_HTML]
#
# NAME|DIR        a profile under profiles/ (dmlex) or a profile directory
# SPEC_DIR        the DocBook source directory (for DMLex, dmlex-v1.0/specification
#                 in oasis-tcs/lexidma)
# OUT_DIR         receives <basename>.md, the images it references and, when
#                 PUBLISHED_HTML is given, <basename>-verification.json
# PUBLISHED_HTML  the published HTML to verify against (path or URL); omit to skip
#
# The source tree is only read: XIncludes are resolved into a temporary
# directory and anything a prebuild generates goes there too.
# Needs: xmllint, python3, pandoc 3.x (verification only), plus what the
# profile's prebuild needs.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
[ "${1:-}" = --profile ] || { echo "usage: build.sh --profile NAME|DIR SPEC_DIR OUT_DIR [PUBLISHED_HTML]" >&2; exit 2; }
PROFILE="$2"; shift 2
[ -d "$PROFILE" ] || PROFILE="$HERE/profiles/$PROFILE"
PROFILE="$(cd "$PROFILE" && pwd)"
[ -f "$PROFILE/profile.json" ] || { echo "no profile.json in $PROFILE" >&2; exit 2; }
SPEC="$(cd "$1" && pwd)"
OUT="$2"
PUB="${3:-}"
mkdir -p "$OUT"
OUT="$(cd "$OUT" && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
mkdir "$WORK/extra"

field() { python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get(sys.argv[2], ""))' "$PROFILE/profile.json" "$1"; }
MAIN="$(field main)"; DTD="$(field dtd)"; ENTITIES="$(field entities)"
IGNORE="$(field merge_log_ignore)"; PREBUILD="$(field prebuild)"; ALLOW="$(field allow)"

# The output name: the profile's basename template filled from the source's entities.
NAME="$(python3 - "$SPEC/$ENTITIES" "$(field basename)" <<'PY'
import re, sys
ents = dict(re.findall(r'<!ENTITY\s+(\w+)\s+"([^"]*)"', open(sys.argv[1], encoding='utf-8').read()))
print(sys.argv[2].format(**ents))
PY
)"
echo "building $NAME from $SPEC (profile $(basename "$PROFILE"))"

# 1. Resolve XIncludes and entities. The module files declare the DocBook DTD by
#    its public URL; a catalog points that at the local copy so nothing is fetched.
cat > "$WORK/catalog.xml" <<XML
<?xml version="1.0"?>
<catalog xmlns="urn:oasis:names:tc:entity:xmlns:xml:catalog">
  <system systemId="http://www.docbook.org/xml/4.5/docbookx.dtd" uri="file://$SPEC/$DTD"/>
  <public publicId="-//OASIS//DTD DocBook XML V4.5//EN" uri="file://$SPEC/$DTD"/>
</catalog>
XML
( cd "$SPEC" && XML_CATALOG_FILES="$WORK/catalog.xml" \
    xmllint --xinclude --noent --loaddtd --nonet "$MAIN" > "$WORK/merged.xml" 2> "$WORK/merge.log" )
grep -v 'validity warning\|^\s\|^\^\|^[a-z]*\s*CDATA' "$WORK/merge.log" > "$WORK/merge.errors" || true
if [ -n "$IGNORE" ]; then grep -vF "$IGNORE" "$WORK/merge.errors" > "$WORK/merge.kept" || true; mv "$WORK/merge.kept" "$WORK/merge.errors"; fi
if grep -qi 'error' "$WORK/merge.errors"; then
  cat "$WORK/merge.log"; echo "merge failed" >&2; exit 2
fi

# 2. The profile's prebuild, for figures the TC's own build generates.
if [ -n "$PREBUILD" ]; then "$PROFILE/$PREBUILD" "$SPEC" "$WORK" "$WORK/extra"; fi

# 3. Convert.
python3 "$HERE/docbook2md.py" "$WORK/merged.xml" "$OUT/$NAME.md" --profile "$PROFILE/profile.json"

# 4. Copy every image the Markdown references, keeping its relative path: from
#    the source tree, or from what the prebuild generated.
python3 - "$OUT/$NAME.md" "$SPEC" "$WORK/extra" "$OUT" <<'PY'
import os, re, shutil, sys
md, spec, extra, out = sys.argv[1:]
n = 0
text = open(md, encoding='utf-8').read()
refs = re.findall(r'!\[[^\]]*\]\(([^)\s]+)\)', text) + re.findall(r'<img\s[^>]*src="([^"]+)"', text)
for p in sorted(set(refs)):
    if p.startswith('http'):
        continue
    src = next((s for s in (os.path.join(extra, p), os.path.join(spec, p)) if os.path.exists(s)), None)
    if src is None:
        sys.exit(f'image missing in source: {p}')
    os.makedirs(os.path.dirname(os.path.join(out, p)) or out, exist_ok=True)
    shutil.copy2(src, os.path.join(out, p)); n += 1
print(f'copied {n} images')
PY

# 5. Verify against the published HTML.
if [ -n "$PUB" ]; then
  python3 "$HERE/../../verify/verify_md.py" "$OUT/$NAME.md" "$PUB" --root "$OUT" \
      ${ALLOW:+--allow "$PROFILE/$ALLOW"} --json "$OUT/$NAME-verification.json"
fi
