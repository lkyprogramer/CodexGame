#!/usr/bin/env bash
# Trial: AtomicChat Ornith-1.5-35B-A3B AD-Q4_K-IQ4_XS on 4090.
# Community: AtomicChat 24GB + context room; analogalok 4090 250k; 3090 AD-Q4_K-IQ4_XS + q4 KV 196k.
# Does not replace WORK. CTX/CTK overridable.
set -euo pipefail
export PATH=/usr/local/cuda/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export LD_LIBRARY_PATH=/usr/local/cuda/lib64:${LD_LIBRARY_PATH:-}

BIN="${LLAMA_SERVER_BIN:-/home/hhtele/llama.cpp-qwen38-20260817/build/bin/llama-server}"
MODEL="${ORNITH_MODEL:-/data/models/qwen/ornith/Ornith-1.5-35B-A3B-AD-Q4_K-IQ4_XS.gguf}"
CTX="${CTX:-200000}"
CTK="${CTK:-q4_0}"
CTV="${CTV:-q4_0}"

exec "$BIN" \
  -m "$MODEL" \
  --alias openclaw/Ornith-1.5-35B-EVAL \
  --host 0.0.0.0 --port 18343 \
  -ngl 999 --split-mode none --main-gpu 0 \
  -c "$CTX" -b 1024 -ub 512 \
  -np 1 -t 12 -fa on --jinja \
  --cache-type-k "$CTK" --cache-type-v "$CTV" \
  --temperature 0.6 --top_p 0.95 --top_k 20 \
  --min_p 0.0 --presence_penalty 0.0 \
  --chat-template-kwargs '{"enable_thinking":true}' \
  --cache-prompt --cache-ram 2048 \
  --metrics --predict 32768 \
  --no-mmproj
