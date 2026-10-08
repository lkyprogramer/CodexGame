#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p validation
python3 -m unittest discover -s tests -v 2>&1 | tee validation/tooling-tests.log
python3 -m compileall -q poc_tools scripts
while IFS= read -r -d '' f; do bash -n "$f"; done < <(find scripts fixtures -name '*.sh' -print0)
python3 scripts/check_bundle.py
