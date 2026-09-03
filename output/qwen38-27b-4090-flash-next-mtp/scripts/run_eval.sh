#!/usr/bin/env bash
# Stop WORK, run F0 then F1, restore WORK.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WORKDIR="${WORKDIR:-/home/hhtele/qwen38-flash-next}"
RESTORE="$ROOT/launch/restore-prod.sh"
trap '"$RESTORE" || true' EXIT
chmod +x "$ROOT"/launch/*.sh
mkdir -p "$WORKDIR/logs" "$WORKDIR/results"

"$ROOT/launch/stop-prod.sh"

run_lane() {
  local lane="$1" launch="$2"
  pkill -f "llama-server.*18443" 2>/dev/null || true
  sleep 2
  nohup "$launch" >"$WORKDIR/logs/${lane}.stdout.log" 2>"$WORKDIR/logs/${lane}.stderr.log" &
  echo $! >"$WORKDIR/logs/${lane}.pid"
  local ready=0
  for i in $(seq 1 180); do
    if ! kill -0 "$(cat "$WORKDIR/logs/${lane}.pid")" 2>/dev/null; then
      echo "$lane died" >&2
      tail -n 80 "$WORKDIR/logs/${lane}.stderr.log" >&2 || true
      return 1
    fi
    if curl -fsS http://127.0.0.1:18443/v1/models >/dev/null 2>&1; then
      ready=1
      echo "$lane ready ${i}s"
      break
    fi
    sleep 3
  done
  [[ "$ready" == 1 ]] || return 1
  nvidia-smi --query-gpu=memory.used,memory.free --format=csv,noheader | tee "$WORKDIR/results/${lane}-vram.txt"
  grep -E "draft acceptance|offloaded|CPU MoE|n_cpu_moe" "$WORKDIR/logs/${lane}.stderr.log" | tail -n 20 || true
  python3 "$ROOT/scripts/bench_fill.py" --lane "$lane" --out "$WORKDIR/results/$lane"
  kill "$(cat "$WORKDIR/logs/${lane}.pid")" 2>/dev/null || true
  sleep 2
}

run_lane F0 "$ROOT/launch/f0-no-mtp.sh"
run_lane F1 "$ROOT/launch/f1-mtp.sh"
echo EVAL_OK
