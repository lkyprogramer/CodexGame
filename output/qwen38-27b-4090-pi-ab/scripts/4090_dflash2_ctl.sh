#!/usr/bin/env bash
# Run ON 4090. start | restore
set -uo pipefail
export LD_LIBRARY_PATH=/home/hhtele/llama.cpp-qwen38-dflash2-pr27342/build/bin:/usr/local/cuda-12.3/lib64:${LD_LIBRARY_PATH:-}
BIN=/home/hhtele/llama.cpp-qwen38-dflash2-pr27342/build/bin/llama-server
MODEL=/data/models/qwen/qwen38/Qwen3.8-27B-UD-Q4_K_XL-dv3.gguf
DRAFT=/data/models/qwen/qwen38/Qwen3.8-27B-DFlash2-Q4_K_M.gguf
WRAP=/home/hhtele/qwen38-dflash2-20260819/launch/sudo-wrap.sh
LOG=/tmp/pi-dflash2.stderr.log
CMD="${1:?start|restore}"
NMAX="${2:-4}"
CTX="${3:-160000}"

restore_prod() {
  pkill -f llama-server 2>/dev/null || true
  sleep 2
  "$WRAP" systemctl start openclaw-qwen38-work-64k.service || true
  for i in $(seq 1 90); do
    curl -fsS http://127.0.0.1:18343/v1/models >/dev/null 2>&1 && { echo prod_ready; return 0; }
    sleep 2
  done
  echo prod_restore_failed
  return 1
}

start_dflash() {
  "$WRAP" systemctl stop openclaw-qwen38-work-64k.service || true
  pkill -f llama-server 2>/dev/null || true
  pkill -f dflash_server 2>/dev/null || true
  sleep 3
  nohup "$BIN" \
    -m "$MODEL" \
    -md "$DRAFT" \
    --alias openclaw/Qwen3.8-27B-WORK \
    --host 127.0.0.1 --port 18343 \
    -ngl 999 --split-mode none --main-gpu 0 \
    -c "$CTX" -b 1024 -ub 512 \
    -np 1 -t 12 -fa on --jinja --no-mmproj \
    --cache-type-k q4_0 --cache-type-v q4_0 \
    --spec-type draft-dflash --spec-draft-n-max "$NMAX" \
    --spec-draft-type-k q4_0 --spec-draft-type-v q4_0 \
    --temperature 1.0 --top_p 0.95 --top_k 20 \
    --min_p 0.0 --presence_penalty 0.0 \
    --reasoning-budget 4096 \
    --chat-template-kwargs '{"enable_thinking":true,"reasoning_effort":"medium","preserve_thinking":false}' \
    --cache-prompt --cache-ram 2048 --slot-prompt-similarity 0.10 \
    --metrics --predict 32768 \
    >/tmp/pi-dflash2.stdout.log 2>"$LOG" &
  echo $! >/tmp/pi-dflash2.pid
  for i in $(seq 1 120); do
    if curl -fsS http://127.0.0.1:18343/v1/models >/dev/null 2>&1; then
      echo dflash2_ready ${i}s nmax=$NMAX ctx=$CTX
      nvidia-smi --query-gpu=memory.used,memory.free --format=csv,noheader
      return 0
    fi
    if ! kill -0 "$(cat /tmp/pi-dflash2.pid)" 2>/dev/null; then
      echo died
      tail -n 50 "$LOG"
      return 1
    fi
    sleep 2
  done
  echo not_ready
  tail -n 50 "$LOG"
  return 1
}

case "$CMD" in
  start) start_dflash ;;
  restore) restore_prod ;;
  *) echo bad; exit 2 ;;
esac
