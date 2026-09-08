#!/usr/bin/env bash
# Run ON 4090. start-off | start-on | restore
set -uo pipefail
export PATH=/usr/local/cuda-12.3/bin:/home/hhtele/bin:$PATH
ROOT=/home/hhtele/lucebox-qwen38-4090
BIN=$ROOT/server/build/dflash_server
IQ4=/data/models/qwen/qwen38-lucebox/Qwen3.8-27B-UD-IQ4_XS.gguf
Q8=/data/models/qwen/qwen38-lucebox/qwen38-dflash2-q8_0.gguf
WRAP=/home/hhtele/qwen38-dflash2-20260819/launch/sudo-wrap.sh
LOG=/home/hhtele/lucebox-qwen38-4090/logs/pi-lucebox.stderr.log
CMD="${1:?start-off|start-on|restore}"

stop_dflash() { pkill -f dflash_server 2>/dev/null || true; sleep 2; }

restore_prod() {
  stop_dflash
  "$WRAP" systemctl start openclaw-qwen38-work-64k.service || true
  for i in $(seq 1 90); do
    curl -fsS http://127.0.0.1:18343/v1/models >/dev/null 2>&1 && { echo prod_ready; return 0; }
    sleep 2
  done
  echo prod_restore_failed
  return 1
}

start_lucebox() {
  local extra=("$@")
  "$WRAP" systemctl stop openclaw-qwen38-work-64k.service || true
  stop_dflash
  nohup env DFLASH_SAMPLED_VERIFY=1 "$BIN" "$IQ4" \
    --draft "$Q8" \
    --target-device cuda:0 --draft-device cuda:0 \
    --draft-block-size 16 \
    --cache-type-k q4_0 --cache-type-v q4_0 \
    --max-ctx 200000 \
    --host 127.0.0.1 --port 18343 \
    --model-name openclaw/Qwen3.8-27B-WORK \
    --prefix-cache-slots 8 \
    --prefill-cache-slots 1 \
    "${extra[@]}" \
    >/home/hhtele/lucebox-qwen38-4090/logs/pi-lucebox.stdout.log 2>"$LOG" &
  echo $! >/home/hhtele/lucebox-qwen38-4090/logs/pi-lucebox.pid
  for i in $(seq 1 120); do
    curl -fsS http://127.0.0.1:18343/v1/models >/dev/null 2>&1 && { echo lucebox_ready ${i}s; return 0; }
    kill -0 "$(cat /home/hhtele/lucebox-qwen38-4090/logs/pi-lucebox.pid)" 2>/dev/null || { echo died; tail -n 40 "$LOG"; return 1; }
    sleep 2
  done
  echo not_ready
  return 1
}

case "$CMD" in
  start-off) start_lucebox ;;
  start-on)  start_lucebox --agent-turn-cache ;;
  restore)   restore_prod ;;
  *) echo "bad cmd $CMD"; exit 2 ;;
esac
