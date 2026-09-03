#!/usr/bin/env bash
# B1: VBR dynamic KV, explicit 200K, floor turbo4 (do not open t1).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=/dev/null
source "$ROOT/common.env"
exec "$BIN_BUUN" \
  -m "$MODEL" \
  --alias "$TRIAL_ALIAS" \
  --host 127.0.0.1 \
  --port "$TRIAL_PORT" \
  -ngl 999 \
  --split-mode none \
  --main-gpu 0 \
  -c 200000 \
  -b 1024 \
  -ub 512 \
  -np 1 \
  -t 12 \
  -fa on \
  --jinja \
  --no-mmproj \
  --cache-type-k vbr \
  --cache-type-v vbr \
  --vbr-floor turbo4 \
  --spec-type draft-mtp \
  --spec-draft-n-max 2 \
  --temperature 1.0 \
  --top_p 0.95 \
  --top_k 20 \
  --min_p 0.0 \
  --presence_penalty 0.0 \
  --reasoning-budget 4096 \
  --reasoning-budget-message "$REASONING_CUTOFF" \
  --chat-template-kwargs '{"enable_thinking":true,"reasoning_effort":"medium","preserve_thinking":false}' \
  --cache-prompt \
  --metrics \
  --predict 32768
