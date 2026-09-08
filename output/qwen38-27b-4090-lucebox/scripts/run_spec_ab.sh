#!/usr/bin/env bash
# Greedy vs sampled vs DDTree A/B on 18343. Trap restores WORK.
set -uo pipefail
export PATH=/usr/local/cuda-12.3/bin:/home/hhtele/bin:$PATH
ROOT=/home/hhtele/lucebox-qwen38-4090
BIN=$ROOT/server/build/dflash_server
IQ4=/data/models/qwen/qwen38-lucebox/Qwen3.8-27B-UD-IQ4_XS.gguf
Q8=/data/models/qwen/qwen38-lucebox/qwen38-dflash2-q8_0.gguf
WRAP=/home/hhtele/qwen38-dflash2-20260819/launch/sudo-wrap.sh
BENCH=/home/hhtele/lucebox-qwen38-4090/scripts/bench_spec.py

mkdir -p "$ROOT/logs" "$ROOT/results/spec-ab" "$ROOT/scripts"
exec >>"$ROOT/logs/spec-ab.out" 2>&1
echo "===== spec-ab start $(date -Is) pid=$$ ====="

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
  local extra_env=() extra_args=()
  for x in "$@"; do
    if [[ "$x" == *=* && "$x" != --* ]]; then
      extra_env+=("$x")
    else
      extra_args+=("$x")
    fi
  done
  pkill -f dflash_server 2>/dev/null || true
  sleep 2
  echo "===== start $lane $(date -Is) env=${extra_env[*]:-} args=${extra_args[*]:-} ====="
  nohup env "${extra_env[@]}" "$BIN" "$IQ4" \
    --draft "$Q8" \
    --target-device cuda:0 --draft-device cuda:0 \
    --draft-block-size 16 \
    --cache-type-k q8_0 --cache-type-v q8_0 \
    --max-ctx 32768 \
    --host 127.0.0.1 --port 18343 \
    --model-name qwen38-lucebox \
    "${extra_args[@]}" \
    >"$ROOT/logs/${lane}.stdout.log" 2>"$ROOT/logs/${lane}.stderr.log" &
  echo $! >"$ROOT/logs/${lane}.pid"
  for i in $(seq 1 90); do
    if curl -fsS http://127.0.0.1:18343/v1/models >/dev/null 2>&1; then
      echo "$lane ready ${i}s"
      return 0
    fi
    if ! kill -0 "$(cat "$ROOT/logs/${lane}.pid")" 2>/dev/null; then
      echo "$lane died"
      tail -n 40 "$ROOT/logs/${lane}.stderr.log"
      return 1
    fi
    sleep 2
  done
  echo "$lane not ready"
  return 1
}

run_lane() {
  local lane="$1" temp="$2"
  shift 2
  start_server "$lane" "$@" || return 1
  python3 "$BENCH" http://127.0.0.1:18343 qwen38-lucebox "$temp" 256 \
    | tee "$ROOT/results/spec-ab/${lane}.jsonl"
  echo "----- $lane log markers -----"
  rg -n "ar-decode|spec-decode|accept|draft |tok/s|block size" "$ROOT/logs/${lane}.stderr.log" | tail -n 40
  kill "$(cat "$ROOT/logs/${lane}.pid")" 2>/dev/null || true
  sleep 2
}

# G0: greedy — must be spec, not AR
run_lane G0 0.0
# G1: greedy + DDTree 28 (4090 Qwen3.5 published path)
run_lane G1 0.0 --ddtree --ddtree-budget 28
# S0: WORK sampler, expect AR
run_lane S0 1.0
# S1: WORK sampler + sampled verify
run_lane S1 1.0 DFLASH_SAMPLED_VERIFY=1

echo "SPEC_AB_OK $(date -Is)"
nvidia-smi --query-gpu=memory.used,memory.free --format=csv,noheader || true
