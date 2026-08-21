#!/usr/bin/env bash
# D0: Analogalok DFlash2 ceiling (n-max 4, q4 KV, 110K) plus safety flags he omitted.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=/dev/null
source "$ROOT/common.env"
exec "$BIN_DFLASH" \
  -m "$MODEL" \
  -md "$DRAFT" \
  --alias "$TRIAL_ALIAS" \
  --host 0.0.0.0 \
  --port "$TRIAL_PORT" \
  --spec-type draft-dflash \
  --spec-draft-n-max 4 \
  -c 110000 \
  -ngl 99 \
  -ctv q4_0 \
  -ctk q4_0 \
  -np 1 \
  -fa on \
  --jinja \
  --no-mmproj \
  --metrics
