#!/usr/bin/env bash
# Pi + HTTP prefix probes against production NInfer on 18343. Does not stop the unit.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RES="$ROOT/results/prod-prefix"
mkdir -p "$RES"
ST="$ROOT/logs/prod-prefix.status"
NOW() { date +%Y-%m-%dT%H:%M:%S; }
echo "PREFIX_PROD_START $(NOW)" | tee -a "$ST"

bash /Users/luo/Documents/github/CodexGame/output/qwen38-27b-4090-pi-ab/scripts/ensure_tunnel.sh

snap() {
  local name="$1"
  curl -fsS --max-time 5 http://127.0.0.1:18343/metrics >"$RES/metrics-$name.txt" || true
  python3 - "$RES/metrics-$name.txt" "$RES/metrics-$name.json" <<'PY'
import json, re, sys
text = open(sys.argv[1], errors="replace").read()
keys = [
    "ninfer:requests_total",
    "ninfer:prefix_cache_hit_tokens_total",
    "ninfer:continuation_lookup_hits_total",
    "ninfer:continuation_lookup_misses_total",
    "ninfer:continuation_stable_prefix_restores_total",
    "ninfer:continuation_preparation_hits_total",
    "llamacpp:prompt_tokens_total",
]
out = {}
for k in keys:
    m = re.search(rf"^{re.escape(k)} (\S+)", text, re.M)
    out[k] = float(m.group(1)) if m else None
json.dump(out, open(sys.argv[2], "w"), indent=2)
print(json.dumps(out))
PY
}

snap before
export SERVER_URL=http://127.0.0.1:18343/v1
export MODEL_ID=openclaw/Qwen3.8-27B-WORK
export PROBE_OUT="$RES/http_probe.json"
python3 "$ROOT/bench/prefix_agent_probe.py"
snap after-http

export THINKING=medium
export RESULTS_ROOT="$RES"
export BACKEND=prod
export PI_CODING_AGENT_DIR="$ROOT/pi-config/prod"
export PI_PROVIDER=work
export PI_MODEL=openclaw/Qwen3.8-27B-WORK
bash "$ROOT/scripts/run_pi_java.sh"
snap after-pi

python3 - "$RES" <<'PY'
import json
from pathlib import Path
res = Path(__import__("sys").argv[1])

def load(p):
    t = Path(p)
    return json.loads(t.read_text()) if t.exists() else {}

b, h, p = load(res/"metrics-before.json"), load(res/"metrics-after-http.json"), load(res/"metrics-after-pi.json")
def d(a,b,k):
    if a.get(k) is None or b.get(k) is None: return None
    return b[k]-a[k]
rows = load(res/"http_probe.json") if (res/"http_probe.json").exists() else []
lines = ["# Production NInfer prefix via Pi + HTTP", "", "## metrics delta", ""]
lines.append("| 区间 | requests | prefix_hit_tokens | cont_hits | cont_misses | stable_prefix_restores |")
lines.append("|---|---:|---:|---:|---:|---:|")
for name, a, b in [("HTTP探针", b, h), ("Pi Java三题", h, p), ("全程", b, p)]:
    lines.append(
        f"| {name} | {d(a,b,'ninfer:requests_total')} | {d(a,b,'ninfer:prefix_cache_hit_tokens_total')} | "
        f"{d(a,b,'ninfer:continuation_lookup_hits_total')} | {d(a,b,'ninfer:continuation_lookup_misses_total')} | "
        f"{d(a,b,'ninfer:continuation_stable_prefix_restores_total')} |"
    )
lines += ["", "## HTTP 对照", ""]
lines.append("| tag | prompt | cached | hit | ttft_s |")
lines.append("|---|---:|---:|---:|---:|")
for r in rows:
    lines.append(f"| {r.get('tag')} | {r.get('prompt_tokens')} | {r.get('cached_tokens')} | {r.get('hit_ratio')} | {r.get('ttft_s')} |")
csv = res/"prod"/"pi_cases.csv"
if csv.exists():
    lines += ["", "## Pi Java", "", csv.read_text()]
(res/"REPORT.md").write_text("\n".join(lines)+"\n")
print((res/"REPORT.md").read_text())
PY
echo "PREFIX_PROD_OK $(NOW)" | tee -a "$ST"
