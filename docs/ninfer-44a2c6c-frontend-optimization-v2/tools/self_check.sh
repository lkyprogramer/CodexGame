#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
export PYTHONDONTWRITEBYTECODE=1
cd "$ROOT"
python3 -m unittest discover -s tests -v
python3 tools/validate_pack.py
