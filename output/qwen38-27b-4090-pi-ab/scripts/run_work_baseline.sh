#!/usr/bin/env bash
# Pi × WORK baseline on LAN via ssh tunnel. WORK stays on 18343.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOGDIR="$ROOT/results/work"
mkdir -p "$LOGDIR"
export LANE=work
bash "$ROOT/scripts/ensure_tunnel.sh"
if ! curl -fsS --max-time 2 http://127.0.0.1:18444/v1/models >/dev/null 2>&1; then
  python3 "$ROOT/scripts/log_proxy.py" "$LOGDIR/proxy.jsonl" \
    >"$LOGDIR/proxy.stdout" 2>"$LOGDIR/proxy.stderr" &
  echo $! >"$LOGDIR/proxy.pid"
  sleep 1
fi
curl -fsS --max-time 5 http://127.0.0.1:18444/v1/models >/dev/null
echo "WORK_BASELINE_START $(date +%Y-%m-%dT%H:%M:%S)" | tee "$LOGDIR/status.txt"
bash "$ROOT/scripts/run_pi_task.sh" P-short
echo "P-short done $(date +%Y-%m-%dT%H:%M:%S)" | tee -a "$LOGDIR/status.txt"
bash "$ROOT/scripts/run_pi_task.sh" P-loop
echo "WORK_BASELINE_OK $(date +%Y-%m-%dT%H:%M:%S)" | tee -a "$LOGDIR/status.txt"
