#!/usr/bin/env bash
# C3: production recipe with only MTP n=6 + p-min 0.82; ctx 92K to keep VRAM safe.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=/dev/null
source "$ROOT/common.env"
exec "$BIN_PROD" \
  -m "$MODEL" \
  --alias "$TRIAL_ALIAS" \
  --host 0.0.0.0 \
  --port "$TRIAL_PORT" \
  -ngl 999 \
  --split-mode none \
  --main-gpu 0 \
  -c 92160 \
  -b 1024 \
  -ub 512 \
  -np 1 \
  -t 12 \
  -fa on \
  --jinja \
  --no-mmproj \
  --cache-type-k q8_0 \
  --cache-type-v q8_0 \
  --spec-default \
  --spec-type draft-mtp \
  --spec-draft-n-max 6 \
  --spec-draft-p-min 0.82 \
  --spec-draft-type-k q8_0 \
  --spec-draft-type-v q8_0 \
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
