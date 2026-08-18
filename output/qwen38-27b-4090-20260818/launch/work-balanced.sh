#!/usr/bin/env bash
# Qwen3.8-27B work-balanced profile for a single RTX 4090 24GB.
# Bind to 19343 only. Do not replace the Qwen3.6 production unit on 18343.
set -euo pipefail

BIN="${LLAMA_SERVER_BIN:-/home/hhtele/llama.cpp-qwen38-20260817/build/bin/llama-server}"
MODEL="${QWEN38_MODEL:-/data/models/qwen/qwen38/Qwen3.8-27B-UD-Q4_K_XL.gguf}"
HOST="${QWEN38_HOST:-127.0.0.1}"
PORT="${QWEN38_PORT:-19343}"
CTX="${QWEN38_CTX:-65536}"

REASONING_CUTOFF=$'You have reached the reasoning budget. Do not restart the analysis. In one line, state the key assumptions, then classify: success | issue | indeterminate. If indeterminate, keep monitoring — do not invent a fix. Otherwise take the next required action now, smallest scoped action first.'

exec "$BIN" \
  -m "$MODEL" \
  --alias openclaw/qwen38-27b-work \
  --host "$HOST" \
  --port "$PORT" \
  -ngl 999 \
  --split-mode none \
  --main-gpu 0 \
  -c "$CTX" \
  -np 1 \
  -t 12 \
  -fa on \
  --jinja \
  --cache-type-k q8_0 \
  --cache-type-v q8_0 \
  --spec-default \
  --spec-type draft-mtp \
  --spec-draft-n-max 2 \
  --spec-draft-type-k q8_0 \
  --spec-draft-type-v q8_0 \
  --temperature 1.0 \
  --top_p 0.95 \
  --top_k 20 \
  --min_p 0.0 \
  --presence_penalty 0.0 \
  --reasoning-budget 16384 \
  --reasoning-budget-message "$REASONING_CUTOFF" \
  --chat-template-kwargs '{"enable_thinking":true,"reasoning_effort":"medium","preserve_thinking":false}' \
  --cache-prompt \
  --cache-ram 2048 \
  --cache-reuse 256 \
  --slot-prompt-similarity 0.10 \
  --metrics \
  --predict 32768 \
  "$@"
