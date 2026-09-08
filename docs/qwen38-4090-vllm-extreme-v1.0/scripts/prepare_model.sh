#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
source "$ROOT/scripts/common.sh"; source_lock
UP="$ROOT/runtime/qwen38-vllm"
[ -d "$UP" ] || "$ROOT/scripts/setup_upstream.sh"
cd "$UP"
log 'building pinned image and running idempotent model preparation'
docker compose build
docker compose run --rm prepare 2>&1 | tee "$ROOT/logs/prepare-model.log"
log 'model preparation finished; upstream verify will run again on server start'
