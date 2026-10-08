#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p results
python3 -m poc_tools.cli preflight --out results/preflight.json
