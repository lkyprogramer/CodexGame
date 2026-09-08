#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export BACKEND=vllm THINKING="${THINKING:-off}"
export SERVER_URL=http://127.0.0.1:18020/v1
export MODEL_ID=qwen3.8-27b
export API_KEY=local-qwen-bench
export PI_PROVIDER=vllm
export PI_MODEL=qwen3.8-27b
RES="${RESULTS_ROOT:-$ROOT/results}/vllm"
mkdir -p "$RES" "$ROOT/logs" "$ROOT/pi-config/vllm"
NOW() { date +%Y-%m-%dT%H:%M:%S; }
echo "COMPARE_VLLM_START thinking=$THINKING $(NOW)" | tee "$ROOT/logs/vllm-${THINKING}.status"

python3 - <<'PY'
import json
from pathlib import Path
p=Path("/Users/luo/Documents/github/CodexGame/output/qwen38-4090-compare/pi-config/vllm")
p.mkdir(parents=True, exist_ok=True)
(p/"models.json").write_text(json.dumps({"providers":{"vllm":{
  "baseUrl":"http://127.0.0.1:18020/v1","api":"openai-completions","apiKey":"local-qwen-bench","authHeader":True,
  "compat":{"supportsDeveloperRole":False,"supportsReasoningEffort":True},
  "models":[{"id":"qwen3.8-27b","name":"vLLM huge-mtp","reasoning":False,"input":["text"],
    "contextWindow":200000,"maxTokens":8192,"cost":{"input":0,"output":0,"cacheRead":0,"cacheWrite":0}}]
}}}, indent=2))
(p/"settings.json").write_text(json.dumps({"defaultProvider":"vllm","defaultModel":"qwen3.8-27b"}))
PY
printf '%s\n' "{\"backend\":\"vllm\",\"model_id\":\"qwen3.8-27b\",\"ctx\":200000,\"kv\":\"kvarn_k4v2\",\"spec\":\"mtp-n3\",\"thinking\":\"$THINKING\"}" >"$RES/meta.json"

restore() {
  echo "RESTORE $(NOW)" | tee -a "$ROOT/logs/vllm.status"
  ssh -o ConnectTimeout=20 hhtele@192.168.10.29 'bash /home/hhtele/qwen38-vllm/4090_vllm_ctl.sh stop-restore' || true
  pkill -f "ssh .*18020:127.0.0.1:18020" 2>/dev/null || true
}
trap restore EXIT

ssh -o ConnectTimeout=20 hhtele@192.168.10.29 'bash /home/hhtele/qwen38-vllm/4090_vllm_ctl.sh start'
pkill -f "ssh .*18020:127.0.0.1:18020" 2>/dev/null || true
ssh -f -N -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 \
  -L 127.0.0.1:18020:127.0.0.1:18020 hhtele@192.168.10.29
echo "waiting vLLM health $(NOW)" | tee -a "$ROOT/logs/vllm.status"
for i in $(seq 1 180); do
  if curl -fsS --max-time 3 -H "Authorization: Bearer local-qwen-bench" http://127.0.0.1:18020/health >/dev/null 2>&1 \
     || curl -fsS --max-time 3 -H "Authorization: Bearer local-qwen-bench" http://127.0.0.1:18020/v1/models >/dev/null 2>&1; then
    echo "VLLM_READY ${i}x5s $(NOW)" | tee -a "$ROOT/logs/vllm.status"
    break
  fi
  if [[ "$i" -eq 180 ]]; then echo VLLM_NOT_READY; ssh hhtele@192.168.10.29 'cd /home/hhtele/qwen38-vllm && docker compose --profile single logs --tail 80 single'; exit 1; fi
  sleep 5
done

python3 "$ROOT/bench/http_bench.py"
python3 "$ROOT/bench/cache_bench.py"
bash "$ROOT/scripts/run_pi_java.sh"
python3 "$ROOT/bench/report_compare.py"
echo "COMPARE_VLLM_OK $(NOW)" | tee -a "$ROOT/logs/vllm.status"
