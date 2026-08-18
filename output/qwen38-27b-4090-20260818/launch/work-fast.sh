#!/usr/bin/env bash
# Low-latency no-think profile. Same weights / MTP / KV as work-balanced.
# Use only for short JSON or tool-name routes. Not the quality default.
set -euo pipefail

BIN="${LLAMA_SERVER_BIN:-/home/hhtele/llama.cpp-qwen38-20260817/build/bin/llama-server}"
MODEL="${QWEN38_MODEL:-/data/models/qwen/qwen38/Qwen3.8-27B-UD-Q4_K_XL.gguf}"
HOST="${QWEN38_HOST:-127.0.0.1}"
PORT="${QWEN38_PORT:-19343}"
CTX="${QWEN38_CTX:-65536}"

exec "$BIN" \
  -m "$MODEL" \
  --alias openclaw/qwen38-27b-fast \
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
  --temperature 0.7 \
  --top_p 0.80 \
  --top_k 20 \
  --min_p 0.0 \
  --presence_penalty 1.5 \
  --chat-template-kwargs '{"enable_thinking":false,"reasoning_effort":"low","preserve_thinking":false}' \
  --cache-prompt \
  --cache-ram 2048 \
  --cache-reuse 256 \
  --slot-prompt-similarity 0.10 \
  --metrics \
  --predict 8192 \
  "$@"
