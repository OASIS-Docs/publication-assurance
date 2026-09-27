#!/usr/bin/env bash
# Copyright 2026 OASIS Open
# SPDX-License-Identifier: Apache-2.0
# Authored by Michael Coletta, Technical Advisor to OASIS Open.
#
# DMLex prebuild: Appendix D embeds dmlex_uml.svg, which the TC Makefile
# generates from the NVH model description. Rebuild it the same way, portably
# (python3 and POSIX tail/sed in place of GNU head -n-1 and the
# #!/usr/bin/python shebang of nvh2dot.py), into EXTRA_DIR, never into the
# source tree. Needs Graphviz dot and m4.
#
# nvh2dot.py walks a Python set, so the order of the diagram's clusters, and
# with it the layout, changes from run to run. PYTHONHASHSEED=0 makes a run
# repeatable; the nodes and edges are the same whatever the order.
#
#   prebuild.sh SPEC_DIR WORK_DIR EXTRA_DIR
set -euo pipefail
SPEC=$1 WORK=$2 EXTRA=$3
cd "$SPEC"
awk '/<programlisting>/,/<\/programlisting>/' schemas/informativeCopiesOf3rdPartySchemas/NVH/dmlex_model_description.nvh \
  | tail -n +2 | sed '$d' | PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1 python3 -W ignore nvh2dot.py > "$WORK/dmlex.dot.content"
sed "s#dmlex.dot.content#$WORK/dmlex.dot.content#" dmlex.dot.m4 | m4 > "$WORK/dmlex.dot"
dot -Tsvg < "$WORK/dmlex.dot" > "$EXTRA/dmlex_uml.svg"
echo "generated dmlex_uml.svg"
