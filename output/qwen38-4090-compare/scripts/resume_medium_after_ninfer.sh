#!/usr/bin/env bash
# Resume thinking=medium from NInfer (WORK already done). Restore WORK on exit.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export THINKING=medium
export RESULTS_ROOT="$ROOT/results/medium"
export SHORT_OUTPUT_TOKENS=768 MID_OUTPUT_TOKENS=768
export LONG_OUTPUT_TOKENS=512 DEEP_OUTPUT_TOKENS=512 CACHE_OUTPUT_TOKENS=512
ST="$ROOT/logs/medium.status"
NOW() { date +%Y-%m-%dT%H:%M:%S; }
echo "COMPARE_MEDIUM_RESUME $(NOW)" | tee -a "$ST"

restore() {
  echo "MEDIUM_RESTORE $(NOW)" | tee -a "$ST"
  ssh -o ConnectTimeout=20 hhtele@192.168.10.29 \
    'bash /tmp/4090_ninfer_stop_restore.sh 2>/dev/null; bash /home/hhtele/qwen38-vllm/4090_vllm_ctl.sh stop-restore 2>/dev/null; true' || true
  pkill -f "ssh .*18030:127.0.0.1:18030" 2>/dev/null || true
  pkill -f "ssh .*18020:127.0.0.1:18020" 2>/dev/null || true
}
trap restore EXIT

bash "$ROOT/scripts/run_compare.sh" ninfer
echo "MEDIUM_NINFER_OK $(NOW)" | tee -a "$ST"
bash "$ROOT/scripts/run_vllm_compare.sh"
echo "MEDIUM_VLLM_OK $(NOW)" | tee -a "$ST"
python3 "$ROOT/bench/report_compare.py"
echo "COMPARE_MEDIUM_OK $(NOW)" | tee -a "$ST"
