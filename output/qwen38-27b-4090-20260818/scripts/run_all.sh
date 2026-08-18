#!/usr/bin/env bash
# Orchestrate S0-S7 on the 4090 host. Production must already be stopped.
set -u
ROOT="${ROOT:-/home/hhtele/qwen38-27b-4090-20260818}"
BIN="${LLAMA_SERVER_BIN:-/home/hhtele/llama.cpp-qwen38-20260817/build/bin/llama-server}"
MODEL="${QWEN38_MODEL:-/data/models/qwen/qwen38/Qwen3.8-27B-UD-Q4_K_XL.gguf}"
PY="$ROOT/scripts/qwen38_work_eval.py"
LOG="$ROOT/logs"
mkdir -p "$LOG" "$ROOT/raw" "$ROOT/results" "$ROOT/reports"
export PYTHONUNBUFFERED=1

SERVER_PID=""
kill_server() {
  if [ -n "${SERVER_PID}" ] && kill -0 "$SERVER_PID" 2>/dev/null; then
    kill -TERM -"$SERVER_PID" 2>/dev/null || kill -TERM "$SERVER_PID" 2>/dev/null || true
    for _ in $(seq 1 20); do
      kill -0 "$SERVER_PID" 2>/dev/null || break
      sleep 1
    done
    kill -KILL -"$SERVER_PID" 2>/dev/null || kill -KILL "$SERVER_PID" 2>/dev/null || true
  fi
  SERVER_PID=""
  pkill -f "llama-server .*19343" 2>/dev/null || true
  sleep 2
}

wait_vram() {
  for _ in $(seq 1 30); do
    used="$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | tr -d ' ')"
    [ "${used:-9999}" -lt 1500 ] && return 0
    sleep 2
  done
  return 0
}

start_work() {
  local ctx="${1:-65536}"
  local kv="${2:-q8_0}"
  local budget="${3:-16384}"
  local alias="${4:-openclaw/qwen38-27b-work}"
  kill_server
  wait_vram
  local cutoff='You have reached the reasoning budget. Do not restart the analysis. In one line, state the key assumptions, then classify: success | issue | indeterminate. If indeterminate, keep monitoring — do not invent a fix. Otherwise take the next required action now, smallest scoped action first.'
  setsid "$BIN" \
    -m "$MODEL" \
    --alias "$alias" \
    --host 127.0.0.1 --port 19343 \
    -ngl 999 --split-mode none --main-gpu 0 \
    -c "$ctx" -np 1 -t 12 -fa on --jinja \
    --cache-type-k "$kv" --cache-type-v "$kv" \
    --spec-default --spec-type draft-mtp --spec-draft-n-max 2 \
    --spec-draft-type-k q8_0 --spec-draft-type-v q8_0 \
    --temperature 1.0 --top_p 0.95 --top_k 20 --min_p 0.0 --presence_penalty 0.0 \
    --reasoning-budget "$budget" \
    --reasoning-budget-message "$cutoff" \
    --chat-template-kwargs '{"enable_thinking":true,"reasoning_effort":"medium","preserve_thinking":false}' \
    --cache-prompt --cache-ram 2048 --cache-reuse 256 \
    --slot-prompt-similarity 0.10 --metrics --predict 32768 \
    >"$LOG/server-${alias//\//-}.stdout.log" 2>"$LOG/server-${alias//\//-}.stderr.log" &
  SERVER_PID=$!
  for _ in $(seq 1 180); do
    if ! kill -0 "$SERVER_PID" 2>/dev/null; then
      echo "server died during load" >&2
      tail -n 40 "$LOG/server-${alias//\//-}.stderr.log" >&2 || true
      return 1
    fi
    if curl -fsS --max-time 2 http://127.0.0.1:19343/v1/models >/dev/null 2>&1; then
      echo "server_ready alias=$alias ctx=$ctx kv=$kv budget=$budget pid=$SERVER_PID"
      return 0
    fi
    sleep 2
  done
  echo "server wait timeout" >&2
  return 1
}

run_py() {
  local name="$1"
  shift
  echo "===== $name $(date -Is) ====="
  python3 "$PY" --output-root "$ROOT" "$@" 2>&1 | tee "$LOG/${name}.console.log"
  local rc=${PIPESTATUS[0]}
  echo "===== $name rc=$rc $(date -Is) ====="
  return "$rc"
}

echo "run_all_start=$(date -Is)" | tee "$LOG/orchestrator.log"
{
  echo "hostname=$(hostname)"
  echo "commit_binary_help_ok=$( $BIN --help 2>/dev/null | grep -c reasoning-budget )"
  nvidia-smi --query-gpu=name,memory.total,memory.used,temperature.gpu --format=csv
  sha256sum "$MODEL"
} | tee -a "$LOG/orchestrator.log"

# S2 first: dedicated servers per MTP lane
run_py s2 --suite s2 || echo "S2_FAILED" | tee -a "$LOG/orchestrator.log"

# S1 + S3 medium/low/xhigh + S4 + S5 + S6 on 64K work-balanced
start_work 65536 q8_0 16384 openclaw/qwen38-27b-work
run_py s1 --suite s1 --external --model-id openclaw/qwen38-27b-work --lane-id s1_work_balanced || echo "S1_FAILED" | tee -a "$LOG/orchestrator.log"
run_py s3 --suite s3 --external --model-id openclaw/qwen38-27b-work --lane-id s3_budget16384 --budget 16384 --s3-profiles medium,low,xhigh || echo "S3_FAILED" | tee -a "$LOG/orchestrator.log"
run_py s3off --suite s3-off --external --model-id openclaw/qwen38-27b-work --lane-id s3_thinking_off || echo "S3OFF_FAILED" | tee -a "$LOG/orchestrator.log"
run_py s4 --suite s4 --external --model-id openclaw/qwen38-27b-work --lane-id s4_work_balanced --repeats 2 || echo "S4_FAILED" | tee -a "$LOG/orchestrator.log"
run_py s5 --suite s5 --external --model-id openclaw/qwen38-27b-work --lane-id s5_q8_ctx64 --s5-targets 8000,32000,56000 || echo "S5_FAILED" | tee -a "$LOG/orchestrator.log"
run_py s6 --suite s6 --external --model-id openclaw/qwen38-27b-work --lane-id s6_cache || echo "S6_FAILED" | tee -a "$LOG/orchestrator.log"

# S3 budget 4096 / 32768, medium only
start_work 65536 q8_0 4096 openclaw/qwen38-27b-b4k
run_py s3b4k --suite s3 --external --model-id openclaw/qwen38-27b-b4k --lane-id s3_budget4096 --budget 4096 --s3-profiles medium || echo "S3_4K_FAILED" | tee -a "$LOG/orchestrator.log"

start_work 65536 q8_0 32768 openclaw/qwen38-27b-b32k
run_py s3b32k --suite s3 --external --model-id openclaw/qwen38-27b-b32k --lane-id s3_budget32768 --budget 32768 --s3-profiles medium || echo "S3_32K_FAILED" | tee -a "$LOG/orchestrator.log"

# S5 f16 32K control
start_work 32768 f16 16384 openclaw/qwen38-27b-longq
run_py s5f16 --suite s5-f16 --external --model-id openclaw/qwen38-27b-longq --lane-id s5_f16_ctx32 --s5-targets 8000,28000 || echo "S5F16_FAILED" | tee -a "$LOG/orchestrator.log"

kill_server
wait_vram
echo "qwen38_tests_done=$(date -Is)" | tee -a "$LOG/orchestrator.log"
