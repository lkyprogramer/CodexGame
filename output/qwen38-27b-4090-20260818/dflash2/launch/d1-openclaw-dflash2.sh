#!/usr/bin/env bash
# D1: fair OpenClaw-shaped DFlash2 (q8 KV, 64K, medium, empty-content patch binary).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=/dev/null
source "$ROOT/common.env"
NMAX="${SPEC_DRAFT_N_MAX:-4}"
CTX="${TRIAL_CTX:-65536}"
exec "$BIN_DFLASH" \
  -m "$MODEL" \
  -md "$DRAFT" \
  --alias "$TRIAL_ALIAS" \
  --host 0.0.0.0 \
  --port "$TRIAL_PORT" \
  -ngl 999 \
  --split-mode none \
  --main-gpu 0 \
  -c "$CTX" \
  -b 1024 \
  -ub 512 \
  -np 1 \
  -t 12 \
  -fa on \
  --jinja \
  --no-mmproj \
  --cache-type-k q8_0 \
  --cache-type-v q8_0 \
  --spec-type draft-dflash \
  --spec-draft-n-max "$NMAX" \
  --temperature 1.0 \
  --top_p 0.95 \
  --top_k 20 \
  --min_p 0.0 \
  --presence_penalty 0.0 \
  --reasoning-budget 4096 \
  --reasoning-budget-message "$REASONING_CUTOFF" \
  --chat-template-kwargs '{"enable_thinking":true,"reasoning_effort":"medium","preserve_thinking":false}' \
  --cache-prompt \
  --cache-ram 2048 \
  --cache-reuse 256 \
  --metrics \
  --predict 32768
