#!/usr/bin/env bash
# Start a trial launch script on :18443, bench it, then kill the trial server.
set -euo pipefail
LANE="${1:?lane id}"
LAUNCH="${2:?launch script}"
MODEL_NAME="${3:-openclaw/Qwen3.8-27B-DFLASH2}"
WORKDIR="${DFLASH2_WORKDIR:-/home/hhtele/qwen38-dflash2-20260819}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOGDIR="$WORKDIR/logs"
OUT="$WORKDIR/results/$LANE"
mkdir -p "$LOGDIR" "$OUT"

pkill -f "llama-server.*18443" 2>/dev/null || true
sleep 1
chmod +x "$LAUNCH"
nohup "$LAUNCH" >"$LOGDIR/${LANE}.stdout.log" 2>"$LOGDIR/${LANE}.stderr.log" &
echo $! >"$LOGDIR/${LANE}.pid"
echo "started $LANE pid=$(cat "$LOGDIR/${LANE}.pid")"

ready=0
for i in $(seq 1 120); do
  if ! kill -0 "$(cat "$LOGDIR/${LANE}.pid")" 2>/dev/null; then
    echo "server died during wait" >&2
    tail -n 80 "$LOGDIR/${LANE}.stderr.log" >&2 || true
    exit 1
  fi
  if curl -fsS http://127.0.0.1:18443/v1/models >/dev/null 2>&1; then
    ready=1
    echo "ready after ${i}s"
    break
  fi
  sleep 2
done
if [[ "$ready" != 1 ]]; then
  echo "server not ready in 240s" >&2
  tail -n 80 "$LOGDIR/${LANE}.stderr.log" >&2 || true
  kill "$(cat "$LOGDIR/${LANE}.pid")" 2>/dev/null || true
  exit 1
fi

python3 "$ROOT/scripts/bench_lane.py" \
  --base http://127.0.0.1:18443 \
  --model "$MODEL_NAME" \
  --lane "$LANE" \
  --out "$OUT" \
  --skip-wait

kill "$(cat "$LOGDIR/${LANE}.pid")" 2>/dev/null || true
sleep 2
pkill -f "llama-server.*18443" 2>/dev/null || true
nvidia-smi --query-gpu=memory.used,memory.free --format=csv,noheader
