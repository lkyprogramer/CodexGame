#!/usr/bin/env bash
# Run AFTER the development tasks have produced configs/qualification.local.json.
set -euo pipefail
cd "$(dirname "$0")/.."
PLAN="${1:-configs/qualification.local.json}"
if [[ ! -s "$PLAN" ]]; then
  echo 'BLOCKED: AI must complete T22 and generate the local qualification command plan; see AGENT_START.md.' >&2
  exit 78
fi
RUN="results/qualify-$(date -u +%Y%m%dT%H%M%SZ)-$$"
mkdir -p logs
ARGS=()
if [[ "${ALLOW_PRODUCTION_PAUSE:-0}" == 1 ]]; then ARGS+=(--allow-production-pause); fi
# 3600s suite budget + up to 120s graceful shutdown; production restore is a separate safety tail.
python3 scripts/guard_gpu.py "${ARGS[@]}" --timeout 3720 -- \
  python3 -m poc_tools.suite --plan "$PLAN" --out-dir "$RUN" --budget 3600
