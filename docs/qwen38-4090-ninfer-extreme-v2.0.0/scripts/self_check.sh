#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m unittest discover -s tests -v
python3 -m compileall -q tools tests
python3 tools/check_bundle.py
for f in scripts/*.sh; do bash -n "$f"; done
