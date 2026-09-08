#!/usr/bin/env bash
# A2: ctx 262144, draft=3, rk4v4-e8. Restore WORK.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export THINKING=off RESULTS_ROOT="$ROOT/results/fusion"
export SHORT_OUTPUT_TOKENS=256 MID_OUTPUT_TOKENS=256
export LONG_OUTPUT_TOKENS=128 DEEP_OUTPUT_TOKENS=128 CACHE_OUTPUT_TOKENS=96
export BACKEND=ninfer-c262k SERVER_URL=http://127.0.0.1:18030/v1 MODEL_ID=qwen3.8-27b
ST="$ROOT/logs/fusion.status"
NOW() { date +%Y-%m-%dT%H:%M:%S; }
echo "FUSION_A2_START $(NOW)" | tee -a "$ST"
scp -o ConnectTimeout=15 \
  /Users/luo/Documents/github/CodexGame/output/qwen38-27b-4090-ninfer/scripts/4090_ninfer_start.sh \
  /Users/luo/Documents/github/CodexGame/output/qwen38-27b-4090-ninfer/scripts/4090_ninfer_stop_restore.sh \
  hhtele@192.168.10.29:/tmp/
ssh hhtele@192.168.10.29 'chmod +x /tmp/4090_ninfer_start.sh /tmp/4090_ninfer_stop_restore.sh'
restore() {
  echo "FUSION_RESTORE $(NOW)" | tee -a "$ST"
  ssh -o ConnectTimeout=20 hhtele@192.168.10.29 'bash /tmp/4090_ninfer_stop_restore.sh' || true
  pkill -f "ssh .*18030:127.0.0.1:18030" 2>/dev/null || true
}
trap restore EXIT
ssh hhtele@192.168.10.29 'NINFER_KEEP=0 DRAFT_TOKENS=3 NINFER_CTX=262144 bash /tmp/4090_ninfer_start.sh'
pkill -f "ssh .*18030:127.0.0.1:18030" 2>/dev/null || true
ssh -f -N -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 \
  -L 127.0.0.1:18030:127.0.0.1:18030 hhtele@192.168.10.29
sleep 1
mkdir -p "$RESULTS_ROOT/ninfer-c262k"
printf '%s\n' '{"backend":"ninfer-c262k","draft_tokens":3,"kv":"rk4v4-e8","ctx":262144,"thinking":"off"}' \
  >"$RESULTS_ROOT/ninfer-c262k/meta.json"
python3 "$ROOT/bench/http_bench.py"
python3 "$ROOT/bench/cache_bench.py"
echo "FUSION_A2_OK $(NOW)" | tee -a "$ST"
