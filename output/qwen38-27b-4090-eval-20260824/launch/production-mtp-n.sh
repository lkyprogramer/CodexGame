#!/usr/bin/env bash
# Trial: current WORK recipe, only --spec-draft-n-max changes.
set -euo pipefail
export PATH=/usr/local/cuda/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export LD_LIBRARY_PATH=/usr/local/cuda/lib64:${LD_LIBRARY_PATH:-}

BIN="${LLAMA_SERVER_BIN:-/home/hhtele/llama.cpp-qwen38-20260817/build/bin/llama-server}"
MODEL="${QWEN38_MODEL:-/data/models/qwen/qwen38/Qwen3.8-27B-UD-Q4_K_XL-dv3.gguf}"
SPEC_N="${SPEC_N:-2}"
REASONING_CUTOFF='Stop thinking. State the answer or the next smallest action now.'

exec "$BIN" \
  -m "$MODEL" \
  --alias openclaw/Qwen3.8-27B-EVAL \
  --host 0.0.0.0 --port 18343 \
  -ngl 999 --split-mode none --main-gpu 0 \
  -c 200000 -b 1024 -ub 512 \
  -np 1 -t 12 -fa on --jinja \
  --cache-type-k q4_0 --cache-type-v q4_0 \
  --spec-default --spec-type draft-mtp --spec-draft-n-max "$SPEC_N" \
  --spec-draft-type-k q4_0 --spec-draft-type-v q4_0 \
  --temperature 1.0 --top_p 0.95 --top_k 20 \
  --min_p 0.0 --presence_penalty 0.0 \
  --reasoning-budget 4096 \
  --reasoning-budget-message "$REASONING_CUTOFF" \
  --chat-template-kwargs '{"enable_thinking":true,"reasoning_effort":"medium","preserve_thinking":false}' \
  --cache-prompt --cache-ram 2048 \
  --slot-prompt-similarity 0.10 \
  --metrics --predict 32768 \
  --no-mmproj
