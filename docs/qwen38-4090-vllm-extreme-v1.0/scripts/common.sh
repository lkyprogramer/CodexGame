#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
mkdir -p "$ROOT/logs" "$ROOT/results" "$ROOT/.state"
load_bench_env() {
  local f="${1:-$ROOT/configs/benchmark.env}"
  [ -f "$f" ] || f="$ROOT/configs/benchmark.env.example"
  set -a; source "$f"; set +a
}
source_lock() { set -a; source "$ROOT/configs/source.lock"; set +a; }
ts() { date '+%Y-%m-%d %H:%M:%S'; }
log() { echo "[$(ts)] $*"; }
