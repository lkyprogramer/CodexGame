#!/usr/bin/env bash
# Stop WORK, run B0-B2 (and B3 if DFlash2 loads), restore WORK.
set -euo pipefail
export BUUN_WORKDIR="${BUUN_WORKDIR:-/home/hhtele/qwen38-buun-20260901}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RESTORE="$ROOT/launch/restore-prod.sh"
trap '"$RESTORE" || true' EXIT

chmod +x "$ROOT"/launch/*.sh "$ROOT"/scripts/*.sh
"$ROOT/launch/stop-prod.sh"

run() {
  local lane="$1" launch="$2" extra="${3:-}"
  bash "$ROOT/scripts/run_lane.sh" "$lane" "$launch" openclaw/Qwen3.8-27B-BUUN $extra
}

run B0 "$ROOT/launch/b0-work-equiv.sh"
run B1 "$ROOT/launch/b1-vbr-turbo4-floor.sh" --with-64k
run B2 "$ROOT/launch/b2-turbo4-pinned.sh" --with-64k

# Probe DFlash2 schema without occupying a full bench if load fails fast.
if timeout 45 "$ROOT/launch/b3-dflash2-q2.sh" >/tmp/buun-b3-probe.log 2>&1; then
  true
fi
if grep -q "schema is unsupported" /tmp/buun-b3-probe.log 2>/dev/null \
   || grep -q "failed to load draft model" /tmp/buun-b3-probe.log 2>/dev/null; then
  echo "B3 skipped: DFlash2 GGUF schema rejected by buun"
  mkdir -p "$BUUN_WORKDIR/results/B3"
  cp /tmp/buun-b3-probe.log "$BUUN_WORKDIR/results/B3/load-fail.log" || true
else
  pkill -f "llama-server.*18443" 2>/dev/null || true
  sleep 1
  run B3 "$ROOT/launch/b3-dflash2-q2.sh" || echo "B3 bench failed (recorded)"
fi
