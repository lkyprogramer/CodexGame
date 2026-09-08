#!/usr/bin/env bash
# run_compare.sh work|ninfer   (vllm skipped)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND="${1:?work|ninfer}"
export BACKEND THINKING="${THINKING:-off}"
NOW() { date +%Y-%m-%dT%H:%M:%S; }
RES="${RESULTS_ROOT:-$ROOT/results}/$BACKEND"
mkdir -p "$RES" "$ROOT/logs"
exec >>"$ROOT/logs/${THINKING}-${BACKEND}.out" 2>&1
echo "===== compare $BACKEND start $(NOW) ====="

ensure_work_tunnel() {
  bash /Users/luo/Documents/github/CodexGame/output/qwen38-27b-4090-pi-ab/scripts/ensure_tunnel.sh
}

case "$BACKEND" in
  work)
    ensure_work_tunnel
    export SERVER_URL=http://127.0.0.1:18343/v1
    export MODEL_ID=openclaw/Qwen3.8-27B-WORK
    export PI_PROVIDER=work
    export PI_MODEL=openclaw/Qwen3.8-27B-WORK
    python3 - <<'PY'
import json
from pathlib import Path
p=Path("/Users/luo/Documents/github/CodexGame/output/qwen38-4090-compare/pi-config/work")
p.mkdir(parents=True, exist_ok=True)
(p/"models.json").write_text(json.dumps({"providers":{"work":{
  "baseUrl":"http://127.0.0.1:18343/v1","api":"openai-completions","apiKey":"sk-local","authHeader":True,
  "compat":{"supportsDeveloperRole":False,"supportsReasoningEffort":False},
  "models":[{"id":"openclaw/Qwen3.8-27B-WORK","name":"WORK","reasoning":False,"input":["text"],
    "contextWindow":200192,"maxTokens":8192,"cost":{"input":0,"output":0,"cacheRead":0,"cacheWrite":0}}]
}}}, indent=2))
(p/"settings.json").write_text(json.dumps({"defaultProvider":"work","defaultModel":"openclaw/Qwen3.8-27B-WORK"}))
PY
    printf '%s\n' "{\"backend\":\"work\",\"model_id\":\"openclaw/Qwen3.8-27B-WORK\",\"ctx\":200192,\"kv\":\"q4\",\"spec\":\"mtp-n2\",\"thinking\":\"$THINKING\"}" >"$RES/meta.json"
    python3 "$ROOT/bench/http_bench.py"
    python3 "$ROOT/bench/cache_bench.py"
    bash "$ROOT/scripts/run_pi_java.sh"
    echo "COMPARE_WORK_OK $(NOW)"
    ;;
  ninfer)
    restore_ninfer() {
      ssh -o ConnectTimeout=20 hhtele@192.168.10.29 'bash /tmp/4090_ninfer_stop_restore.sh' || true
      pkill -f "ssh .*18030:127.0.0.1:18030" 2>/dev/null || true
    }
    trap restore_ninfer EXIT
    scp -o ConnectTimeout=15 \
      /Users/luo/Documents/github/CodexGame/output/qwen38-27b-4090-ninfer/scripts/4090_ninfer_start.sh \
      /Users/luo/Documents/github/CodexGame/output/qwen38-27b-4090-ninfer/scripts/4090_ninfer_stop_restore.sh \
      hhtele@192.168.10.29:/tmp/
    ssh hhtele@192.168.10.29 'chmod +x /tmp/4090_ninfer_start.sh /tmp/4090_ninfer_stop_restore.sh; bash /tmp/4090_ninfer_start.sh'
    pkill -f "ssh .*18030:127.0.0.1:18030" 2>/dev/null || true
    ssh -f -N -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 \
      -L 127.0.0.1:18030:127.0.0.1:18030 hhtele@192.168.10.29
    sleep 1
    export SERVER_URL=http://127.0.0.1:18030/v1
    export MODEL_ID=qwen3.8-27b
    export PI_PROVIDER=ninfer
    export PI_MODEL=qwen3.8-27b
    python3 - <<'PY'
import json
from pathlib import Path
p=Path("/Users/luo/Documents/github/CodexGame/output/qwen38-4090-compare/pi-config/ninfer")
p.mkdir(parents=True, exist_ok=True)
(p/"models.json").write_text(json.dumps({"providers":{"ninfer":{
  "baseUrl":"http://127.0.0.1:18030/v1","api":"openai-completions","apiKey":"sk-local","authHeader":True,
  "compat":{"supportsDeveloperRole":False,"supportsReasoningEffort":True},
  "models":[{"id":"qwen3.8-27b","name":"NInfer","reasoning":False,"input":["text"],
    "contextWindow":221184,"maxTokens":8192,"cost":{"input":0,"output":0,"cacheRead":0,"cacheWrite":0}}]
}}}, indent=2))
(p/"settings.json").write_text(json.dumps({"defaultProvider":"ninfer","defaultModel":"qwen3.8-27b"}))
PY
    printf '%s\n' "{\"backend\":\"ninfer\",\"model_id\":\"qwen3.8-27b\",\"ctx\":221184,\"kv\":\"rk4v4-e8\",\"spec\":\"mtp-n3\",\"thinking\":\"$THINKING\"}" >"$RES/meta.json"
    python3 "$ROOT/bench/http_bench.py"
    python3 "$ROOT/bench/cache_bench.py"
    bash "$ROOT/scripts/run_pi_java.sh"
    ssh hhtele@192.168.10.29 'bash /tmp/4090_ninfer_stop_restore.sh' || true
    pkill -f "ssh .*18030:127.0.0.1:18030" 2>/dev/null || true
    echo "COMPARE_NINFER_OK $(NOW)"
    ;;
  *) echo "unknown $BACKEND"; exit 2 ;;
esac
python3 "$ROOT/bench/report_compare.py" || true
