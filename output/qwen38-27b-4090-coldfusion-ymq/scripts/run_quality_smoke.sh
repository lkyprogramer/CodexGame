#!/usr/bin/env bash
# Quality smoke: same bench_lane as DFlash2/buun, YMQ-M at 200K MTP n=2, then restore WORK.
set -uo pipefail
export PATH=/usr/local/cuda/bin:/home/hhtele/bin:/usr/sbin:/usr/bin:/sbin:/bin
ROOT=/home/hhtele/qwen38-coldfusion-ymq
BIN=/home/hhtele/llama.cpp-qwen38-20260817/build/bin/llama-server
MODEL=/data/models/qwen/qwen38-coldfusion-ymq/Qwen3.8-27B-Cold-Fusion-GAIN-V1.1-YMQ-M.gguf
WRAP=/home/hhtele/qwen38-dflash2-20260819/launch/sudo-wrap.sh
BENCH=/home/hhtele/qwen38-buun-20260901/scripts/bench_lane.py
REASONING_CUTOFF='Stop thinking. State the answer or the next smallest action now.'

mkdir -p "$ROOT/logs" "$ROOT/results/quality-smoke"
exec >>"$ROOT/logs/quality-smoke.out" 2>&1
echo "===== quality smoke start $(date -Is) pid=$$ ====="

restore_prod() {
  echo "===== restore_prod $(date -Is) ====="
  pkill -f "llama-server.*18443" 2>/dev/null || true
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
  echo "prod_restore_failed" >&2
  return 1
}
trap 'echo "===== EXIT trap $(date -Is) ====="; restore_prod || true' EXIT

if [[ -x "$WRAP" ]]; then
  "$WRAP" systemctl stop openclaw-qwen38-work-64k.service || true
else
  sudo systemctl stop openclaw-qwen38-work-64k.service || true
fi
pkill -f "llama-server.*18443" 2>/dev/null || true
sleep 3

nohup "$BIN" \
  -m "$MODEL" \
  --alias qwen38-coldfusion-ymq \
  --host 127.0.0.1 --port 18443 \
  -ngl 999 --split-mode none --main-gpu 0 \
  -c 200192 -np 1 -fa on --jinja --no-mmproj \
  --cache-type-k q4_0 --cache-type-v q4_0 \
  --ctx-checkpoints 4 \
  --spec-type draft-mtp --spec-draft-n-max 2 \
  --spec-draft-type-k q4_0 --spec-draft-type-v q4_0 \
  --temperature 1.0 --top_p 0.95 --top_k 20 --repeat-penalty 1.0 \
  --reasoning-budget 4096 --reasoning-budget-message "$REASONING_CUTOFF" \
  --chat-template-kwargs '{"enable_thinking":true,"reasoning_effort":"medium","preserve_thinking":false}' \
  -t 12 --metrics --predict 32768 \
  >"$ROOT/logs/smoke-server.stdout.log" 2>"$ROOT/logs/smoke-server.stderr.log" &
echo $! >"$ROOT/logs/smoke-server.pid"

ready=0
for i in $(seq 1 90); do
  if curl -fsS http://127.0.0.1:18443/v1/models >/dev/null 2>&1; then
    ready=1
    echo "ready ${i}s"
    break
  fi
  sleep 2
done
if [[ "$ready" != 1 ]]; then
  echo "server not ready"
  tail -n 50 "$ROOT/logs/smoke-server.stderr.log"
  exit 1
fi
nvidia-smi --query-gpu=memory.used,memory.free --format=csv,noheader | tee "$ROOT/results/quality-smoke/vram.txt"
python3 "$BENCH" --base http://127.0.0.1:18443 --model qwen38-coldfusion-ymq --lane quality-smoke --out "$ROOT/results/quality-smoke" --skip-wait --with-64k
echo "SMOKE_OK $(date -Is)"
python3 - <<'PY'
import json
from pathlib import Path
p=Path("/home/hhtele/qwen38-coldfusion-ymq/results/quality-smoke/summary.json")
print(p.read_text()[:4000] if p.exists() else "no summary")
PY
kill "$(cat "$ROOT/logs/smoke-server.pid")" 2>/dev/null || true
sleep 2
