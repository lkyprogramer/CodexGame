#!/usr/bin/env bash
# Deep C3 MTP knob study. Restores production on exit.
set -uo pipefail
WORKDIR="${DFLASH2_WORKDIR:-/home/hhtele/qwen38-dflash2-20260819}"
export DFLASH2_WORKDIR="$WORKDIR"
ROOT="$WORKDIR"
LOGDIR="$WORKDIR/logs"
mkdir -p "$LOGDIR" "$WORKDIR/results/c3-deep"
WRAP="$ROOT/launch/sudo-wrap.sh"

restore() {
  echo "=== restore prod $(date -Iseconds) ==="
  pkill -f "llama-server.*--port 18443" 2>/dev/null || true
  sleep 1
  "$WRAP" systemctl start openclaw-qwen38-work-64k.service || true
  for i in $(seq 1 90); do
    if curl -fsS http://127.0.0.1:18343/v1/models >/dev/null 2>&1; then
      echo "prod_ready after ${i}s"
      return 0
    fi
    sleep 2
  done
  echo "prod_restore_failed" >&2
}
trap restore EXIT

run_live() {
  local lane="$1" base="$2" model="$3"
  echo "=== $lane live $(date -Iseconds) ==="
  python3 "$ROOT/scripts/c3_deep_eval.py" \
    --base "$base" --model "$model" --lane "$lane" \
    --out "$WORKDIR/results/c3-deep/$lane"
}

run_trial() {
  local lane="$1" nmax="$2" ctx="$3" pmin="$4"
  echo "=== $lane n=$nmax pmin=${pmin:-none} ctx=$ctx $(date -Iseconds) ==="
  pkill -f "llama-server.*--port 18443" 2>/dev/null || true
  sleep 1
  export SPEC_DRAFT_N_MAX="$nmax"
  export TRIAL_CTX="$ctx"
  if [[ -n "$pmin" ]]; then
    export SPEC_DRAFT_P_MIN="$pmin"
  else
    unset SPEC_DRAFT_P_MIN || true
  fi
  nohup bash "$ROOT/launch/mtp-knob.sh" \
    >"$LOGDIR/${lane}.stdout.log" 2>"$LOGDIR/${lane}.stderr.log" &
  echo $! >"$LOGDIR/${lane}.pid"
  ready=0
  for i in $(seq 1 90); do
    if ! kill -0 "$(cat "$LOGDIR/${lane}.pid")" 2>/dev/null; then
      echo "server died $lane" >&2
      tail -n 60 "$LOGDIR/${lane}.stderr.log" >&2 || true
      return 1
    fi
    if curl -fsS http://127.0.0.1:18443/v1/models >/dev/null 2>&1; then
      ready=1
      echo "ready after ${i}s"
      break
    fi
    sleep 2
  done
  if [[ "$ready" != 1 ]]; then
    echo "not ready $lane" >&2
    tail -n 80 "$LOGDIR/${lane}.stderr.log" >&2 || true
    kill "$(cat "$LOGDIR/${lane}.pid")" 2>/dev/null || true
    return 1
  fi
  nvidia-smi --query-gpu=memory.used,memory.free --format=csv,noheader | tee "$WORKDIR/results/c3-deep/${lane}.vram.txt"
  python3 "$ROOT/scripts/c3_deep_eval.py" \
    --base http://127.0.0.1:18443 \
    --model openclaw/Qwen3.8-27B-DFLASH2 \
    --lane "$lane" \
    --out "$WORKDIR/results/c3-deep/$lane" \
    --skip-wait
  local rc=$?
  kill "$(cat "$LOGDIR/${lane}.pid")" 2>/dev/null || true
  sleep 2
  pkill -f "llama-server.*--port 18443" 2>/dev/null || true
  return $rc
}

echo "=== C3 deep start $(date -Iseconds) ==="
run_live P0_n2_112k http://127.0.0.1:18343 openclaw/Qwen3.8-27B-WORK

echo "=== stop prod $(date -Iseconds) ==="
"$WRAP" systemctl stop openclaw-qwen38-work-64k.service
sleep 2
nvidia-smi --query-gpu=memory.used,memory.free --format=csv,noheader

# Candidate at production window first.
if ! run_trial n6p82_112k 6 112000 0.82; then
  echo "112K n=6 failed, falling back to 92K for remaining lanes"
  run_trial n2_92k 2 92160 ""
  run_trial n6p82_92k 6 92160 0.82
  run_trial n6p0_92k 6 92160 ""
  run_trial n2p82_92k 2 92160 0.82
  run_trial n4p82_92k 4 92160 0.82
else
  run_trial n6p0_112k 6 112000 ""
  run_trial n2p82_112k 2 112000 0.82
  run_trial n4p82_112k 4 112000 0.82
  run_trial n6p82_92k 6 92160 0.82
fi

echo "=== c3 deep done $(date -Iseconds) ==="
