#!/usr/bin/env bash
# Trial D: analogalok DFlash2 Q2_K + 250K + KV q4 + --parallel 1 + n-max 3.
# Reproduces https://x.com/analogalok/status/2090797011100717267
set -euo pipefail
export PATH=/usr/local/cuda/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export LD_LIBRARY_PATH=/usr/local/cuda/lib64:${LD_LIBRARY_PATH:-}

BIN="${LLAMA_SERVER_BIN:-/home/hhtele/llama.cpp-qwen38-20260817/build/bin/llama-server}"
MODEL="${QWEN38_V3_MODEL:-/data/models/qwen/qwen38/Qwen3.8-27B-UD-Q4_K_XL-dv3.gguf}"
DRAFT="${DFLASH2_Q2:-/data/models/qwen/qwen38/Qwen3.8-27B-DFlash2-Q2_K.gguf}"
CTX="${CTX:-250000}"
REASONING_CUTOFF='Stop thinking. State the answer or the next smallest action now.'

exec "$BIN" \
  -m "$MODEL" \
  -md "$DRAFT" \
  --alias openclaw/Qwen3.8-27B-EVAL \
  --host 0.0.0.0 --port 18343 \
  -ngl 999 --spec-draft-ngl 99 \
  --split-mode none --main-gpu 0 \
  -c "$CTX" \
  --parallel 1 -np 1 \
  -t 12 -fa on --jinja \
  --cache-type-k q4_0 --cache-type-v q4_0 \
  --spec-type draft-dflash \
  --spec-draft-n-max 3 \
  --spec-draft-n-min 1 \
  --temperature 1.0 --top_p 0.95 --top_k 20 \
  --min_p 0.0 --presence_penalty 0.0 \
  --reasoning-budget 4096 \
  --reasoning-budget-message "$REASONING_CUTOFF" \
  --chat-template-kwargs '{"enable_thinking":true,"reasoning_effort":"medium","preserve_thinking":false}' \
  --metrics --predict 32768 \
  --no-mmproj
