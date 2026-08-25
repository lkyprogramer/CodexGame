#!/usr/bin/env bash
# Eval candidate on 18343. Same knobs as WORK. Not for boot.
set -euo pipefail

export PATH=/usr/local/cuda/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export LD_LIBRARY_PATH=/usr/local/cuda/lib64:${LD_LIBRARY_PATH:-}

CANDIDATE="${CANDIDATE:?set CANDIDATE=sharp|grug|fable|salience|coldfusion}"
BIN="${LLAMA_SERVER_BIN:-/home/hhtele/llama.cpp-qwen38-20260817/build/bin/llama-server}"
EVAL="${EVAL_DIR:-/data/models/qwen/qwen38-eval}"
WORK_GGUF="${QWEN38_MODEL:-/data/models/qwen/qwen38/Qwen3.8-27B-UD-Q4_K_XL.gguf}"
CTX="${CTX:-112000}"
REASONING_CUTOFF='Stop thinking. State the answer or the next smallest action now.'

MTP_ARGS=(--spec-default --spec-type draft-mtp --spec-draft-n-max 2
          --spec-draft-type-k q8_0 --spec-draft-type-v q8_0)
TEMPLATE_ARGS=()
MODEL=""

case "$CANDIDATE" in
  sharp)
    MODEL="$WORK_GGUF"
    TEMPLATE_ARGS=(--chat-template-file "$EVAL/templates/chat_template.jinja")
    ;;
  grug)
    MODEL="$EVAL/grug-v1.1/grug-27b-v1.1-Q4_K_M.gguf"
    MTP_ARGS=()
    ;;
  fable)
    MODEL="$EVAL/fable-distill/Qwen3.8-27B-Fable-Distill-Q4_K_M.gguf"
    ;;
  salience)
    MODEL="$EVAL/salience-r5/vectionlabs_Salience-27B-R5-Q4_K_M.gguf"
    ;;
  coldfusion)
    MODEL="${COLDFUSION_GGUF:-$EVAL/cold-fusion-v1.1/Qwen3.8-27B-Cold-Fusion-GAIN-V1.1-NM-DAU-NEO-MAX-NEO-MTP-Q4_K_M.gguf}"
    ;;
  *)
    echo "unknown CANDIDATE=$CANDIDATE" >&2
    exit 1
    ;;
esac

if [[ ! -f "$MODEL" ]]; then
  echo "model file missing: $MODEL" >&2
  exit 1
fi
if [[ "$CANDIDATE" == "sharp" && ! -f "$EVAL/templates/chat_template.jinja" ]]; then
  echo "sharp template missing" >&2
  exit 1
fi

exec "$BIN" \
  -m "$MODEL" \
  --alias openclaw/Qwen3.8-27B-EVAL \
  --host 0.0.0.0 --port 18343 \
  -ngl 999 --split-mode none --main-gpu 0 \
  -c "$CTX" -b 1024 -ub 512 \
  -np 1 -t 12 -fa on --jinja \
  --cache-type-k q8_0 --cache-type-v q8_0 \
  "${MTP_ARGS[@]}" \
  --temperature 1.0 --top_p 0.95 --top_k 20 \
  --min_p 0.0 --presence_penalty 0.0 \
  --reasoning-budget 4096 \
  --reasoning-budget-message "$REASONING_CUTOFF" \
  --chat-template-kwargs '{"enable_thinking":true,"reasoning_effort":"medium","preserve_thinking":false}' \
  --cache-prompt --cache-ram 2048 --cache-reuse 256 \
  --slot-prompt-similarity 0.10 \
  --metrics --predict 32768 \
  "${TEMPLATE_ARGS[@]}"
