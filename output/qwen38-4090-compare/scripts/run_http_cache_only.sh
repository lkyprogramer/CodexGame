#!/usr/bin/env bash
# Re-run Stage1+2 only. Java already collected. BACKEND=work|ninfer
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND="${1:?work|ninfer}"
export BACKEND THINKING=off
RES="$ROOT/results/$BACKEND"
mkdir -p "$RES" "$ROOT/logs"
rm -rf "$ROOT/.state/prompts"
echo "HTTP_CACHE_$BACKEND START $(date +%Y-%m-%dT%H:%M:%S)" | tee -a "$ROOT/logs/http.status"

case "$BACKEND" in
  work)
    bash /Users/luo/Documents/github/CodexGame/output/qwen38-27b-4090-pi-ab/scripts/ensure_tunnel.sh
    export SERVER_URL=http://127.0.0.1:18343/v1 MODEL_ID=openclaw/Qwen3.8-27B-WORK
    python3 "$ROOT/bench/http_bench.py"
    python3 "$ROOT/bench/cache_bench.py"
    echo "HTTP_CACHE_WORK_OK $(date +%Y-%m-%dT%H:%M:%S)" | tee -a "$ROOT/logs/http.status"
    ;;
  ninfer)
    restore() {
      ssh -o ConnectTimeout=20 hhtele@192.168.10.29 'bash /tmp/4090_ninfer_stop_restore.sh' || true
      pkill -f "ssh .*18030:127.0.0.1:18030" 2>/dev/null || true
    }
    trap restore EXIT
    scp -o ConnectTimeout=15 \
      /Users/luo/Documents/github/CodexGame/output/qwen38-27b-4090-ninfer/scripts/4090_ninfer_start.sh \
      /Users/luo/Documents/github/CodexGame/output/qwen38-27b-4090-ninfer/scripts/4090_ninfer_stop_restore.sh \
      hhtele@192.168.10.29:/tmp/
    ssh hhtele@192.168.10.29 'chmod +x /tmp/4090_ninfer_start.sh /tmp/4090_ninfer_stop_restore.sh; bash /tmp/4090_ninfer_start.sh'
    pkill -f "ssh .*18030:127.0.0.1:18030" 2>/dev/null || true
    ssh -f -N -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 \
      -L 127.0.0.1:18030:127.0.0.1:18030 hhtele@192.168.10.29
    sleep 1
    export SERVER_URL=http://127.0.0.1:18030/v1 MODEL_ID=qwen3.8-27b
    python3 "$ROOT/bench/http_bench.py"
    python3 "$ROOT/bench/cache_bench.py"
    echo "HTTP_CACHE_NINFER_OK $(date +%Y-%m-%dT%H:%M:%S)" | tee -a "$ROOT/logs/http.status"
    ;;
esac
python3 "$ROOT/bench/report_compare.py" || true
