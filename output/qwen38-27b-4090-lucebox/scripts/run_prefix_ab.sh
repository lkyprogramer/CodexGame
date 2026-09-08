#!/usr/bin/env bash
# A/B prefix-cache vs agent-turn-cache vs no cache. 200K q4 sampled. Trap restores WORK.
set -uo pipefail
export PATH=/usr/local/cuda-12.3/bin:/home/hhtele/bin:$PATH
ROOT=/home/hhtele/lucebox-qwen38-4090
BIN=$ROOT/server/build/dflash_server
IQ4=/data/models/qwen/qwen38-lucebox/Qwen3.8-27B-UD-IQ4_XS.gguf
Q8=/data/models/qwen/qwen38-lucebox/qwen38-dflash2-q8_0.gguf
WRAP=/home/hhtele/qwen38-dflash2-20260819/launch/sudo-wrap.sh
BENCH=$ROOT/scripts/bench_prefix_agent.py
OFFICIAL=$ROOT/server/scripts/benchmark_tool_prefix_cache.py
CTX=200000
OUT=$ROOT/results/prefix-ab

mkdir -p "$ROOT/logs" "$OUT" "$ROOT/scripts"
exec >>"$ROOT/logs/prefix-ab.out" 2>&1
echo "===== prefix-ab start $(date -Is) pid=$$ ====="

restore_prod() {
  echo "===== restore_prod $(date -Is) ====="
  pkill -f "dflash_server" 2>/dev/null || true
  sleep 2
  if [[ -x "$WRAP" ]]; then
    "$WRAP" systemctl start openclaw-qwen38-work-64k.service || true
  else
    sudo systemctl start openclaw-qwen38-work-64k.service || true
  fi
  for i in $(seq 1 90); do
    if curl -fsS http://127.0.0.1:18343/v1/models >/dev/null 2>&1; then
      echo "prod_ready after ${i}s"
      return 0
    fi
    sleep 2
  done
  echo prod_restore_failed
  return 1
}
trap 'echo "===== EXIT trap $(date -Is) ====="; restore_prod || true' EXIT

test -x "$BIN"
test -s "$IQ4"
test -s "$Q8"
test -f "$BENCH"

if [[ -x "$WRAP" ]]; then
  "$WRAP" systemctl stop openclaw-qwen38-work-64k.service || true
else
  sudo systemctl stop openclaw-qwen38-work-64k.service || true
fi
pkill -f dflash_server 2>/dev/null || true
sleep 3

start_server() {
  local lane="$1"
  shift
  pkill -f dflash_server 2>/dev/null || true
  sleep 2
  echo "===== start $lane $(date -Is) extra=$* ====="
  nohup env DFLASH_SAMPLED_VERIFY=1 "$BIN" "$IQ4" \
    --draft "$Q8" \
    --target-device cuda:0 --draft-device cuda:0 \
    --draft-block-size 16 \
    --cache-type-k q4_0 --cache-type-v q4_0 \
    --max-ctx "$CTX" \
    --host 127.0.0.1 --port 18343 \
    --model-name qwen38-lucebox \
    "$@" \
    >"$ROOT/logs/${lane}.stdout.log" 2>"$ROOT/logs/${lane}.stderr.log" &
  echo $! >"$ROOT/logs/${lane}.pid"
  for i in $(seq 1 120); do
    if curl -fsS http://127.0.0.1:18343/v1/models >/dev/null 2>&1; then
      echo "$lane ready ${i}s"
      nvidia-smi --query-gpu=memory.used,memory.free --format=csv,noheader | tee "$OUT/${lane}.vram.txt"
      rg -n "prefix_cache|agent_turn|max_ctx|cache_type" "$ROOT/logs/${lane}.stderr.log" | head -n 20 || true
      return 0
    fi
    if ! kill -0 "$(cat "$ROOT/logs/${lane}.pid")" 2>/dev/null; then
      echo "$lane died"
      tail -n 60 "$ROOT/logs/${lane}.stderr.log"
      return 1
    fi
    sleep 2
  done
  echo "$lane not ready"
  tail -n 60 "$ROOT/logs/${lane}.stderr.log"
  return 1
}

run_lane() {
  local lane="$1"
  shift
  start_server "$lane" "$@" || return 1
  echo "----- official $lane -----"
  python3 "$OFFICIAL" --url http://127.0.0.1:18343 --model qwen38-lucebox \
    --warm-turns 3 --min-speedup 0.01 --json-out "$OUT/${lane}.official.json" \
    || echo "official_exit_$?"
  echo "----- realistic $lane -----"
  python3 "$BENCH" http://127.0.0.1:18343 qwen38-lucebox "$OUT" "$lane" \
    | tee "$OUT/${lane}.jsonl"
  echo "----- $lane CACHE/spec markers -----"
  rg -n "chat CACHE|agent-turn-cache|spec-decode|ar-decode|capping verify|cudaMalloc" \
    "$ROOT/logs/${lane}.stderr.log" | tail -n 80 || true
  kill "$(cat "$ROOT/logs/${lane}.pid")" 2>/dev/null || true
  sleep 2
}

run_lane P0_nocache --prefix-cache-slots 0
run_lane P1_prefix --prefix-cache-slots 32
run_lane P2_agent --prefix-cache-slots 32 --agent-turn-cache

echo "PREFIX_AB_OK $(date -Is)"
nvidia-smi --query-gpu=memory.used,memory.free --format=csv,noheader || true
