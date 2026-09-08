#!/usr/bin/env bash
# Run one Pi print-mode task against the tunneled 4090 backend.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PATH="/Users/luo/.nvm/versions/node/v22.19.0/bin:$PATH"
export PI_CODING_AGENT_DIR="$ROOT/pi-config"
export PI_OFFLINE=1
TASK_ID="${1:?task id}"
PROMPT_FILE="$ROOT/prompts/${TASK_ID}.txt"
OUT_DIR="$ROOT/results/${LANE:-work}"
mkdir -p "$OUT_DIR"
test -f "$PROMPT_FILE"
cd /Users/luo/Documents/github/CodexGame
{
  echo "===== $TASK_ID lane=${LANE:-work} $(date +%Y-%m-%dT%H:%M:%S) ====="
  /usr/bin/time -p pi --print --provider openclaw --model openclaw/Qwen3.8-27B-WORK \
    --no-extensions --no-skills --thinking off --approve \
    --session-dir "$OUT_DIR/sessions" --name "$TASK_ID" \
    -- "$(cat "$PROMPT_FILE")"
} >"$OUT_DIR/${TASK_ID}.out" 2>"$OUT_DIR/${TASK_ID}.err"
echo "exit:$?" | tee -a "$OUT_DIR/${TASK_ID}.err"
