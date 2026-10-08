#!/usr/bin/env bash
# A baseline / B checkpoints 8 / C soak / D rk8v4. Always restore ninfer prod.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
NINFER_SCRIPTS="/Users/luo/Documents/github/CodexGame/output/qwen38-27b-4090-ninfer/scripts"
HOST="hhtele@192.168.10.29"
RES="$ROOT/results/rewrite"
ST="$ROOT/logs/rewrite.status"
LOG="$ROOT/logs/rewrite-suite.out"
NOW() { date +%Y-%m-%dT%H:%M:%S; }
mkdir -p "$RES" "$ROOT/logs"
exec >>"$LOG" 2>&1
echo "REWRITE_START $(NOW)" | tee -a "$ST"

scp -o ConnectTimeout=15 \
  "$NINFER_SCRIPTS/4090_ninfer_start.sh" \
  "$NINFER_SCRIPTS/4090_ninfer_stop_restore.sh" \
  "$HOST:/tmp/"
ssh -o ConnectTimeout=15 "$HOST" 'chmod +x /tmp/4090_ninfer_start.sh /tmp/4090_ninfer_stop_restore.sh'

restore() {
  echo "REWRITE_RESTORE $(NOW)" | tee -a "$ST"
  ssh -o ConnectTimeout=20 "$HOST" 'bash /tmp/4090_ninfer_stop_restore.sh' || true
  pkill -f "ssh .*18030:127.0.0.1:18030" 2>/dev/null || true
}
trap restore EXIT

tunnel() {
  pkill -f "ssh .*18030:127.0.0.1:18030" 2>/dev/null || true
  sleep 1
  ssh -f -N -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 \
    -L 127.0.0.1:18030:127.0.0.1:18030 "$HOST"
  sleep 1
  curl -fsS --max-time 5 http://127.0.0.1:18030/v1/models >/dev/null
}

start_ninfer() {
  local ckpt="$1" kv="$2" ctx="$3"
  echo "REWRITE_BOOT ckpt=$ckpt kv=$kv ctx=$ctx $(NOW)" | tee -a "$ST"
  ssh -o ConnectTimeout=20 "$HOST" \
    "NINFER_KEEP=0 DRAFT_TOKENS=3 NINFER_CTX=$ctx NINFER_KV=$kv NINFER_TURN_CKPT=$ckpt NINFER_REQUEST_LOG=/var/log/ninfer/ninfer-request.jsonl bash /tmp/4090_ninfer_start.sh"
}

export SERVER_URL=http://127.0.0.1:18030/v1
export MODEL_ID=qwen3.8-27b
export THINKING=medium
export NINFER_JSONL_HOST=/home/hhtele/ninfer-4090/logs/ninfer-request.jsonl

# --- A ---
start_ninfer 0 rk4v4-e8 262144
tunnel
echo "REWRITE_A_READY $(NOW)" | tee -a "$ST"
python3 "$ROOT/bench/rewrite_workload.py" --phase A --out "$RES/phase_a.json"
echo "REWRITE_A_OK $(NOW)" | tee -a "$ST"

# --- B ---
start_ninfer 8 rk4v4-e8 262144
tunnel
echo "REWRITE_B_READY $(NOW)" | tee -a "$ST"
python3 "$ROOT/bench/rewrite_workload.py" --phase B --out "$RES/phase_b.json"
echo "REWRITE_B_OK $(NOW)" | tee -a "$ST"

# --- C soak: two Java cases (turns add up) + cancel/retry + reminder HTTP ---
echo "REWRITE_C_START $(NOW)" | tee -a "$ST"
export RESULTS_ROOT="$RES"
export BACKEND=soak
export PI_CODING_AGENT_DIR="$ROOT/pi-config/ninfer"
export PI_PROVIDER=ninfer
export PI_MODEL=qwen3.8-27b
export PI_CODING_AGENT_DIR="$ROOT/pi-config/ninfer"
# keep checkpoint-8 server
python3 - <<'PY' || true
import json, time, urllib.request, os
url=os.environ["SERVER_URL"]+"/chat/completions"
body={"model":os.environ["MODEL_ID"],"messages":[{"role":"user","content":"Count slowly to 200."}],
      "max_tokens":256,"stream":True,"reasoning_effort":"medium"}
req=urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type":"application/json"})
t0=time.monotonic()
try:
    r=urllib.request.urlopen(req, timeout=8)
    r.read(64)
    r.close()
    print("CANCEL_STREAM_OK", round(time.monotonic()-t0,2))
except Exception as e:
    print("CANCEL_STREAM", type(e).__name__, e)
# retry
body["max_tokens"]=32
req=urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type":"application/json"})
urllib.request.urlopen(req, timeout=120).read(200)
print("RETRY_OK")
PY
bash "$ROOT/scripts/run_pi_java.sh" || true
echo "REWRITE_C_OK $(NOW)" | tee -a "$ST"

# --- D rk8 ---
start_ninfer 0 rk8v4 200192
tunnel
echo "REWRITE_D_READY $(NOW)" | tee -a "$ST"
export BACKEND=ninfer-rk8
export RESULTS_ROOT="$RES"
python3 "$ROOT/bench/http_bench.py" || true
export BACKEND=ninfer-rk8
bash "$ROOT/scripts/run_pi_java.sh" || true
echo "REWRITE_D_OK $(NOW)" | tee -a "$ST"

python3 "$ROOT/scripts/summarize_rewrite.py" || true
echo "REWRITE_SUITE_OK $(NOW)" | tee -a "$ST"
