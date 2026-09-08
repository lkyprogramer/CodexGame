#!/usr/bin/env bash
# P0 fusion: A2 262k (+L1 sweep) -> Java -> A2b L3+restart -> A3 rk2v4-e8+Java.
# Always restore WORK. thinking=off HTTP ladder + cache_bench.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
NINFER_SCRIPTS="/Users/luo/Documents/github/CodexGame/output/qwen38-27b-4090-ninfer/scripts"
HOST="hhtele@192.168.10.29"
export THINKING=off RESULTS_ROOT="$ROOT/results/fusion"
export SHORT_OUTPUT_TOKENS=256 MID_OUTPUT_TOKENS=256
export LONG_OUTPUT_TOKENS=128 DEEP_OUTPUT_TOKENS=128 CACHE_OUTPUT_TOKENS=96
export SERVER_URL=http://127.0.0.1:18030/v1 MODEL_ID=qwen3.8-27b
export PI_PROVIDER=ninfer PI_MODEL=qwen3.8-27b
export PI_CODING_AGENT_DIR="$ROOT/pi-config/ninfer"
ST="$ROOT/logs/fusion.status"
LOG="$ROOT/logs/fusion-p0.out"
NOW() { date +%Y-%m-%dT%H:%M:%S; }
mkdir -p "$ROOT/logs" "$RESULTS_ROOT"
exec >>"$LOG" 2>&1
echo "FUSION_P0_START $(NOW)" | tee -a "$ST"

scp -o ConnectTimeout=15 \
  "$NINFER_SCRIPTS/4090_ninfer_start.sh" \
  "$NINFER_SCRIPTS/4090_ninfer_stop_restore.sh" \
  "$HOST:/tmp/"
ssh -o ConnectTimeout=15 "$HOST" 'chmod +x /tmp/4090_ninfer_start.sh /tmp/4090_ninfer_stop_restore.sh'

restore() {
  echo "FUSION_RESTORE $(NOW)" | tee -a "$ST"
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

write_pi_ctx() {
  python3 - "$1" <<'PY'
import json, sys
from pathlib import Path
ctx = int(sys.argv[1])
p = Path("/Users/luo/Documents/github/CodexGame/output/qwen38-4090-compare/pi-config/ninfer")
p.mkdir(parents=True, exist_ok=True)
(p / "models.json").write_text(json.dumps({"providers": {"ninfer": {
    "baseUrl": "http://127.0.0.1:18030/v1", "api": "openai-completions",
    "apiKey": "sk-local", "authHeader": True,
    "compat": {"supportsDeveloperRole": False, "supportsReasoningEffort": True},
    "models": [{"id": "qwen3.8-27b", "name": "NInfer", "reasoning": False,
                "input": ["text"], "contextWindow": ctx, "maxTokens": 8192,
                "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0}}]
}}}, indent=2) + "\n")
(p / "settings.json").write_text(json.dumps({
    "defaultProvider": "ninfer", "defaultModel": "qwen3.8-27b"
}) + "\n")
PY
}

start_ninfer() {
  local ctx="$1" kv="$2" l1="$3" cache="$4"
  echo "FUSION_START ctx=$ctx kv=$kv l1=$l1 cache=$cache $(NOW)" | tee -a "$ST"
  set +e
  ssh -o ConnectTimeout=20 "$HOST" \
    "NINFER_KEEP=0 DRAFT_TOKENS=3 NINFER_CTX=$ctx NINFER_KV=$kv NINFER_L1_MIB=$l1 NINFER_CACHE=$cache bash /tmp/4090_ninfer_start.sh"
  local rc=$?
  set -e
  return "$rc"
}

run_benches() {
  local backend="$1"
  export BACKEND="$backend"
  mkdir -p "$RESULTS_ROOT/$backend"
  python3 "$ROOT/bench/http_bench.py"
  python3 "$ROOT/bench/cache_bench.py"
  curl -fsS --max-time 5 http://127.0.0.1:18030/metrics >"$RESULTS_ROOT/$backend/metrics.txt" || true
}

run_java() {
  local backend="$1"
  export BACKEND="$backend"
  set +e
  bash "$ROOT/scripts/run_pi_java.sh"
  set -e
}

A2_L1=""
A2_BACKEND=""
for L1 in 6144 4096 2048 768; do
  if start_ninfer 262144 rk4v4-e8 "$L1" l1-l2; then
    A2_L1="$L1"
    A2_BACKEND="ninfer-c262k-l1${L1}"
    echo "FUSION_A2_READY l1=$L1 $(NOW)" | tee -a "$ST"
    tunnel
    write_pi_ctx 262144
    mkdir -p "$RESULTS_ROOT/$A2_BACKEND"
    printf '%s\n' "{\"backend\":\"$A2_BACKEND\",\"draft_tokens\":3,\"kv\":\"rk4v4-e8\",\"ctx\":262144,\"l1_mib\":$L1,\"cache\":\"l1-l2\",\"thinking\":\"off\"}" \
      >"$RESULTS_ROOT/$A2_BACKEND/meta.json"
    run_benches "$A2_BACKEND"
    echo "FUSION_A2_HTTP_OK $A2_BACKEND $(NOW)" | tee -a "$ST"
    run_java "$A2_BACKEND"
    echo "FUSION_A2_JAVA_OK $A2_BACKEND $(NOW)" | tee -a "$ST"
    break
  fi
  echo "FUSION_A2_BOOT_FAIL l1=$L1 $(NOW)" | tee -a "$ST"
done

if [[ -n "$A2_L1" ]]; then
  if start_ninfer 262144 rk4v4-e8 "$A2_L1" l1-l2-l3; then
    echo "FUSION_A2B_READY l1=$A2_L1 $(NOW)" | tee -a "$ST"
    tunnel
    A2B="ninfer-c262k-l3"
    mkdir -p "$RESULTS_ROOT/$A2B"
    printf '%s\n' "{\"backend\":\"$A2B\",\"draft_tokens\":3,\"kv\":\"rk4v4-e8\",\"ctx\":262144,\"l1_mib\":$A2_L1,\"cache\":\"l1-l2-l3\",\"thinking\":\"off\"}" \
      >"$RESULTS_ROOT/$A2B/meta.json"
    run_benches "$A2B"
    echo "FUSION_A2B_HTTP_OK $(NOW)" | tee -a "$ST"
    if start_ninfer 262144 rk4v4-e8 "$A2_L1" l1-l2-l3; then
      tunnel
      A2BR="ninfer-c262k-l3-restart"
      mkdir -p "$RESULTS_ROOT/$A2BR"
      printf '%s\n' "{\"backend\":\"$A2BR\",\"note\":\"same L3 volume after container recreate\",\"l1_mib\":$A2_L1}" \
        >"$RESULTS_ROOT/$A2BR/meta.json"
      export BACKEND="$A2BR"
      python3 "$ROOT/bench/cache_bench.py"
      echo "FUSION_A2B_RESTART_OK $(NOW)" | tee -a "$ST"
    else
      echo "FUSION_A2B_RESTART_BOOT_FAIL $(NOW)" | tee -a "$ST"
    fi
  else
    echo "FUSION_A2B_BOOT_FAIL $(NOW)" | tee -a "$ST"
  fi
else
  echo "FUSION_A2_ALL_L1_FAIL $(NOW)" | tee -a "$ST"
fi

A3_L1="${A2_L1:-6144}"
A3_OK=0
if start_ninfer 262144 rk2v4-e8 "$A3_L1" l1-l2; then
  A3_OK=1
else
  for L1 in 6144 4096 2048 768; do
    [[ "$L1" == "$A3_L1" ]] && continue
    if start_ninfer 262144 rk2v4-e8 "$L1" l1-l2; then
      A3_L1="$L1"
      A3_OK=1
      break
    fi
    echo "FUSION_A3_BOOT_FAIL l1=$L1 $(NOW)" | tee -a "$ST"
  done
fi
if [[ "$A3_OK" == 1 ]]; then
  echo "FUSION_A3_READY l1=$A3_L1 $(NOW)" | tee -a "$ST"
  tunnel
  write_pi_ctx 262144
  A3B="ninfer-rk2-c262k"
  mkdir -p "$RESULTS_ROOT/$A3B"
  printf '%s\n' "{\"backend\":\"$A3B\",\"draft_tokens\":3,\"kv\":\"rk2v4-e8\",\"ctx\":262144,\"l1_mib\":$A3_L1,\"cache\":\"l1-l2\",\"thinking\":\"off\"}" \
    >"$RESULTS_ROOT/$A3B/meta.json"
  run_benches "$A3B"
  echo "FUSION_A3_HTTP_OK $(NOW)" | tee -a "$ST"
  run_java "$A3B"
  echo "FUSION_A3_JAVA_OK $(NOW)" | tee -a "$ST"
else
  echo "FUSION_A3_ALL_FAIL $(NOW)" | tee -a "$ST"
fi

python3 "$ROOT/scripts/summarize_fusion_p0.py" || true
if [[ -z "$A2_L1" && "$A3_OK" != 1 ]]; then
  echo "FUSION_P0_FAIL $(NOW)" | tee -a "$ST"
  exit 1
fi
echo "FUSION_P0_OK $(NOW)" | tee -a "$ST"
