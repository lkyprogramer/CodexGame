#!/usr/bin/env bash
# C2: gavwhittaker MTP without mmproj.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=/dev/null
source "$ROOT/common.env"
exec "$BIN_PROD" \
  -m "$MODEL" \
  --no-mmproj \
  --alias "$TRIAL_ALIAS" \
  --host 0.0.0.0 \
  --port "$TRIAL_PORT" \
  -ngl 99 \
  -c 92160 \
  --cache-type-k q8_0 \
  --cache-type-v q8_0 \
  -fa on \
  -b 2048 \
  -ub 1024 \
  --temp 0.6 \
  --top_p 0.95 \
  --top_k 20 \
  --min_p 0.0 \
  --jinja \
  --reasoning-preserve \
  --reasoning-format deepseek \
  --presence_penalty 0.0 \
  -t 4 \
  --threads-batch 4 \
  --prio 3 \
  --parallel 1 \
  --spec-type draft-mtp \
  --spec-draft-n-max 6 \
  --spec-draft-p-min 0.82 \
  -np 1 \
  --no-webui \
  --metrics
