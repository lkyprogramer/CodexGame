#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=/dev/null
source "$ROOT/common.env"
exec "$BIN" \
  -m "$MODEL" \
  --alias qwen38-flash-next \
  --host 127.0.0.1 --port 18443 \
  -ngl 999 --n-cpu-moe 34 \
  -c 65536 -np 1 -fa on --jinja --no-mmproj \
  --cache-type-k q8_0 --cache-type-v q8_0 \
  --spec-type none \
  -t 12 \
  --metrics --predict 2048
