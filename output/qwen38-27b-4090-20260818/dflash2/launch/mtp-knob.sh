#!/usr/bin/env bash
# Production-shaped MTP with overridable n-max / p-min / ctx. Port 18443 only.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=/dev/null
source "$ROOT/common.env"
NMAX="${SPEC_DRAFT_N_MAX:-6}"
CTX="${TRIAL_CTX:-112000}"
PMIN="${SPEC_DRAFT_P_MIN:-}"
EXTRA=()
if [[ -n "$PMIN" ]]; then
  EXTRA+=(--spec-draft-p-min "$PMIN")
fi
exec "$BIN_PROD" \
  -m "$MODEL" \
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
  --spec-default \
  --spec-type draft-mtp \
  --spec-draft-n-max "$NMAX" \
  "${EXTRA[@]}" \
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
  --slot-prompt-similarity 0.10 \
  --metrics \
  --predict 32768
