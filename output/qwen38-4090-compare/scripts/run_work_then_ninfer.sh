#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "$ROOT/logs"
echo "COMPARE_SUITE_START $(date +%Y-%m-%dT%H:%M:%S)" | tee "$ROOT/logs/suite.status"
bash "$ROOT/scripts/run_compare.sh" work
bash "$ROOT/scripts/run_compare.sh" ninfer
python3 "$ROOT/bench/report_compare.py"
echo "COMPARE_SUITE_OK $(date +%Y-%m-%dT%H:%M:%S)" | tee -a "$ROOT/logs/suite.status"
