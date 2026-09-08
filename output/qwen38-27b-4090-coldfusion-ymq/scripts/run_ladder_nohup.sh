#!/usr/bin/env bash
# Download is assumed done. Stop WORK, ctx ladder C0/C1/C2 (C3 if C2 OOM), restore WORK.
set -uo pipefail
export PATH=/usr/local/cuda/bin:/home/hhtele/bin:/usr/sbin:/usr/bin:/sbin:/bin
ROOT=/home/hhtele/qwen38-coldfusion-ymq
BIN=/home/hhtele/llama.cpp-qwen38-20260817/build/bin/llama-server
MODEL=/data/models/qwen/qwen38-coldfusion-ymq/Qwen3.8-27B-Cold-Fusion-GAIN-V1.1-YMQ-M.gguf
WRAP=/home/hhtele/qwen38-dflash2-20260819/launch/sudo-wrap.sh
REASONING_CUTOFF='Stop thinking. State the answer or the next smallest action now.'

mkdir -p "$ROOT/logs" "$ROOT/results"
exec >>"$ROOT/logs/ladder.out" 2>&1
echo "===== ladder start $(date -Is) pid=$$ ====="

restore_prod() {
  echo "===== restore_prod $(date -Is) ====="
  pkill -f "llama-server.*18443" 2>/dev/null || true
  sleep 2
  if [[ -x "$WRAP" ]]; then
    "$WRAP" systemctl start openclaw-qwen38-work-64k.service || true
  else
    sudo systemctl start openclaw-qwen38-work-64k.service || true
  fi
  for i in $(seq 1 90); do
    if curl -fsS http://127.0.0.1:18343/v1/models >/dev/null 2>&1; then
      echo "prod_ready after ${i}s"
      curl -fsS http://127.0.0.1:18343/v1/models || true
      nvidia-smi --query-gpu=memory.used,memory.free --format=csv,noheader || true
      return 0
    fi
    sleep 2
  done
  echo "prod_restore_failed" >&2
  return 1
}
trap 'echo "===== EXIT trap $(date -Is) status=$? ====="; restore_prod || true' EXIT

test -x "$BIN"
test -s "$MODEL"
ls -lh "$MODEL"

stop_prod() {
  echo "===== stop_prod $(date -Is) ====="
  if [[ -x "$WRAP" ]]; then
    "$WRAP" systemctl stop openclaw-qwen38-work-64k.service || true
  else
    sudo systemctl stop openclaw-qwen38-work-64k.service || true
  fi
  pkill -f "llama-server.*18443" 2>/dev/null || true
  sleep 3
}

wait_ready() {
  local pidfile="$1" logfile="$2"
  local pid
  pid=$(cat "$pidfile")
  for i in $(seq 1 120); do
    if ! kill -0 "$pid" 2>/dev/null; then
      echo "server died"
      tail -n 80 "$logfile" || true
      return 1
    fi
    if curl -fsS http://127.0.0.1:18443/v1/models >/dev/null 2>&1; then
      echo "ready after ${i}s"
      return 0
    fi
    sleep 2
  done
  echo "not ready"
  tail -n 80 "$logfile" || true
  return 1
}

run_cfg() {
  local lane="$1" ctx="$2" mtp="$3"
  echo "===== lane $lane ctx=$ctx mtp=$mtp $(date -Is) ====="
  pkill -f "llama-server.*18443" 2>/dev/null || true
  sleep 2
  local args=(
    "$BIN" -m "$MODEL"
    --alias qwen38-coldfusion-ymq
    --host 127.0.0.1 --port 18443
    -ngl 999 --split-mode none --main-gpu 0
    -c "$ctx" -np 1 -fa on --jinja --no-mmproj
    --cache-type-k q4_0 --cache-type-v q4_0
    --ctx-checkpoints 4 --checkpoint-min-step 2048
    --temperature 1.0 --top_p 0.95 --top_k 20 --repeat-penalty 1.0
    --reasoning-budget 4096 --reasoning-budget-message "$REASONING_CUTOFF"
    --chat-template-kwargs '{"enable_thinking":true,"reasoning_effort":"medium","preserve_thinking":false}'
    -t 12 --metrics --predict 32768
  )
  if [[ "$mtp" == "on" ]]; then
    args+=(--spec-type draft-mtp --spec-draft-n-max 2 --spec-draft-type-k q4_0 --spec-draft-type-v q4_0)
  fi
  nohup "${args[@]}" >"$ROOT/logs/${lane}.stdout.log" 2>"$ROOT/logs/${lane}.stderr.log" &
  echo $! >"$ROOT/logs/${lane}.pid"
  if ! wait_ready "$ROOT/logs/${lane}.pid" "$ROOT/logs/${lane}.stderr.log"; then
    echo "LOAD_FAIL $lane"
    echo "$lane OOM_or_fail" | tee "$ROOT/results/${lane}-fail.txt"
    return 1
  fi
  nvidia-smi --query-gpu=memory.used,memory.free --format=csv,noheader | tee "$ROOT/results/${lane}-vram.txt"
  curl -fsS http://127.0.0.1:18443/v1/models | tee "$ROOT/results/${lane}-models.json"
  python3 "$ROOT/scripts/bench_ctx.py" --lane "$lane" --n-ctx "$ctx" --out "$ROOT/results/$lane"
  kill "$(cat "$ROOT/logs/${lane}.pid")" 2>/dev/null || true
  sleep 2
  pkill -f "llama-server.*18443" 2>/dev/null || true
  sleep 2
  return 0
}

stop_prod
run_cfg C0 200192 on || true
run_cfg C1 245760 on || true
if run_cfg C2 262144 on; then
  echo "C2_OK native 262144 + MTP"
else
  echo "C2_FAIL try C3 no MTP"
  run_cfg C3 262144 off || true
fi

echo "LADDER_OK $(date -Is)"
ls -l "$ROOT/results"
