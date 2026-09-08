#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
source "$ROOT/scripts/common.sh"; load_bench_env "${1:-}"
mkdir -p "$ROOT/logs" "$ROOT/results"
START=$(date +%s)
log "suite start; hard cap=${SUITE_TIMEOUT_SEC}s quick=${QUICK_ONLY:-0}"
run_stage() {
  local name=$1; shift
  local elapsed=$(( $(date +%s)-START )); local remain=$(( SUITE_TIMEOUT_SEC-elapsed ))
  (( remain > 30 )) || { log "suite deadline reached before $name"; return 124; }
  log "stage=$name remain=${remain}s"
  timeout "$remain" "$@" 2>&1 | tee "$ROOT/logs/$name.log"
}
run_stage wait-server "$ROOT/scripts/wait_server.sh"
run_stage http python3 "$ROOT/bench/http_bench.py" "${1:-$ROOT/configs/benchmark.env}"
if [ "${QUICK_ONLY:-0}" != 1 ]; then
  run_stage cache python3 "$ROOT/bench/cache_bench.py" "${1:-$ROOT/configs/benchmark.env}"
  run_stage pi "$ROOT/scripts/run_pi_bench.sh" "${1:-$ROOT/configs/benchmark.env}"
fi
python3 "$ROOT/bench/report.py" | tee "$ROOT/logs/report.log"
log "suite complete elapsed=$(( $(date +%s)-START ))s"
