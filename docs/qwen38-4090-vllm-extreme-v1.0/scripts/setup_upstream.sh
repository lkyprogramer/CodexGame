#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
source "$ROOT/scripts/common.sh"; source_lock
DST="$ROOT/runtime/qwen38-vllm"
mkdir -p "$ROOT/runtime"
if [ ! -d "$DST/.git" ]; then
  log "cloning $UPSTREAM_REPO"
  git clone "$UPSTREAM_REPO" "$DST"
fi
cd "$DST"
git fetch --all --tags --prune
git checkout --detach "$UPSTREAM_COMMIT"
actual=$(git rev-parse HEAD)
[ "$actual" = "$UPSTREAM_COMMIT" ] || { echo "revision mismatch: $actual"; exit 4; }
log "upstream pinned: $actual"
