#!/usr/bin/env bash
# Text-gen HauhauCS Aggressive. CTX/CTK/PORT overridable for probing.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=/dev/null
source "$ROOT/common.env"
CTX="${TRIAL_CTX:-160000}"
CTK="${TRIAL_CTK:-q4_0}"
CTV="${TRIAL_CTV:-q4_0}"
BIND="${TRIAL_PORT:-$PORT}"
exec "$BIN" \
  -m "$MODEL" \
  --alias "$ALIAS" \
  --host 0.0.0.0 \
  --port "$BIND" \
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
  --cache-type-k "$CTK" \
  --cache-type-v "$CTV" \
  --spec-default \
  --spec-type draft-mtp \
  --spec-draft-n-max 2 \
  --spec-draft-type-k q8_0 \
  --spec-draft-type-v q8_0 \
  --temperature 0.7 \
  --top_p 0.80 \
  --top_k 20 \
  --min_p 0.0 \
  --presence_penalty 1.5 \
  --chat-template-kwargs '{"enable_thinking":false,"reasoning_effort":"low","preserve_thinking":false}' \
  --cache-prompt \
  --cache-ram 2048 \
  --cache-reuse 256 \
  --metrics \
  --predict 32768
