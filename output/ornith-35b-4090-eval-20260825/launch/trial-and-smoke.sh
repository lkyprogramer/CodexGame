#!/usr/bin/env bash
# Load Ornith trial on 18343, protocol smoke, optional QCB smoke, restore WORK.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LAUNCH="$ROOT/launch"
LOG="$ROOT/logs"
PIDFILE="$LOG/eval.pid"
SUDO_PASS="${SUDO_PASS:-hhtele}"
QCB_ROOT="${QCB_ROOT:-/home/hhtele/qcb-4090}"
MODEL="${ORNITH_MODEL:-/data/models/qwen/ornith/Ornith-1.5-35B-A3B-AD-Q4_K-IQ4_XS.gguf}"
EXPECT_SHA="${ORNITH_SHA:-6def24b4ef1436f080403b8c0fa9ca3b593abc080c74e64ef7c72d3d6a7322f1}"
mkdir -p "$LOG"

log() { echo "[$(date -u +%FT%TZ)] $*" | tee -a "$LOG/trial-and-smoke.log"; }
sudo_cmd() { echo "$SUDO_PASS" | sudo -S -p "" "$@"; }

stop_eval() {
  if [[ -f "$PIDFILE" ]]; then
    local pid; pid="$(cat "$PIDFILE" || true)"
    if [[ -n "${pid:-}" ]] && kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
      sleep 2
      kill -9 "$pid" 2>/dev/null || true
    fi
    rm -f "$PIDFILE"
  fi
  local i
  for i in $(seq 1 40); do
    ss -ltn | grep -q ':18343 ' || return 0
    sleep 1
  done
}

start_trial() {
  local name="$1"
  stop_eval
  log "start $name CTX=${CTX:-} CTK=${CTK:-}"
  nohup "$LAUNCH/production-ornith-trial.sh" >>"$LOG/eval-$name.out" 2>&1 &
  echo $! >"$PIDFILE"
  local i
  for i in $(seq 1 180); do
    if curl -sf --max-time 2 http://127.0.0.1:18343/v1/models | grep -q 'Ornith-1.5-35B-EVAL'; then
      log "$name up (${i}s)"
      return 0
    fi
    if ! kill -0 "$(cat "$PIDFILE" 2>/dev/null || echo)" 2>/dev/null; then
      log "ERROR $name died (${i}s)"
      tail -n 60 "$LOG/eval-$name.out" | tee -a "$LOG/trial-and-smoke.log" || true
      return 1
    fi
    sleep 2
  done
  log "ERROR $name did not come up"
  tail -n 60 "$LOG/eval-$name.out" | tee -a "$LOG/trial-and-smoke.log" || true
  return 1
}

restore_work() {
  log "restore WORK"
  stop_eval || true
  sudo_cmd systemctl start openclaw-qwen38-work-64k.service || true
  local i
  for i in $(seq 1 60); do
    if curl -sf --max-time 3 http://127.0.0.1:18343/v1/models | grep -q 'Qwen3.8-27B-WORK'; then
      log "WORK restored"
      return 0
    fi
    sleep 2
  done
  log "WARN WORK restore not confirmed"
}

bench_protocol() {
  local tag="$1"
  python3 - "$tag" "$LOG/bench-$tag.json" "$LOG/eval-$tag.out" <<'PY'
import json, time, urllib.request, sys, subprocess, re
tag, out, slog = sys.argv[1], sys.argv[2], sys.argv[3]

def gpu():
    p=subprocess.check_output(["nvidia-smi","--query-gpu=memory.used,memory.free,temperature.gpu,power.draw","--format=csv,noheader,nounits"], text=True).strip()
    used,free,temp,pwr=[x.strip() for x in p.split(",")]
    return {"used_mib":float(used),"free_mib":float(free),"temp_c":float(temp),"power_w":float(pwr)}

def log_pos():
    try:
        return open(slog,"rb").seek(0,2)
    except FileNotFoundError:
        return 0

def scrape(pos):
    rec={}
    try:
        with open(slog,"rb") as f:
            f.seek(pos)
            text=f.read().decode("utf-8","replace")
    except FileNotFoundError:
        return rec
    ev=re.findall(r"eval time =\s+[\d.]+ ms /\s+(\d+) tokens \(\s*[\d.]+ ms per token,\s+([\d.]+) tokens per second\)", text)
    pr=re.findall(r"prompt eval time =\s+[\d.]+ ms /\s+(\d+) tokens \(\s*[\d.]+ ms per token,\s+([\d.]+) tokens per second\)", text)
    if ev:
        rec["eval_tokens"]=int(ev[-1][0]); rec["eval_tok_s"]=float(ev[-1][1])
    if pr:
        rec["prompt_tokens"]=int(pr[-1][0]); rec["prompt_tok_s"]=float(pr[-1][1])
    return rec

def post(payload, timeout=180):
    req=urllib.request.Request("http://127.0.0.1:18343/v1/chat/completions",
        data=json.dumps(payload).encode(), headers={"Content-Type":"application/json"})
    t0=time.time()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        body=json.loads(r.read().decode())
    return body, time.time()-t0

models=json.loads(urllib.request.urlopen("http://127.0.0.1:18343/v1/models", timeout=5).read().decode())
meta=((models.get("data") or [{}])[0].get("meta") or {})
g0=gpu()
rows=[]
cases=[
  ("fib", {
    "model":"openclaw/Ornith-1.5-35B-EVAL",
    "messages":[{"role":"user","content":"Write a Python function that returns the nth Fibonacci number. Code only."}],
    "max_tokens":256,
    "chat_template_kwargs":{"enable_thinking":True},
  }),
  ("tools", {
    "model":"openclaw/Ornith-1.5-35B-EVAL",
    "messages":[{"role":"user","content":"Call the tool get_time with timezone UTC."}],
    "tools":[{"type":"function","function":{"name":"get_time","description":"current time","parameters":{"type":"object","properties":{"timezone":{"type":"string"}},"required":["timezone"]}}}],
    "max_tokens":256,
    "chat_template_kwargs":{"enable_thinking":True},
  }),
  ("think", {
    "model":"openclaw/Ornith-1.5-35B-EVAL",
    "messages":[{"role":"user","content":"Explain in 8 bullets how MoE expert routing affects VRAM vs decode speed on a 24GB GPU."}],
    "max_tokens":512,
    "chat_template_kwargs":{"enable_thinking":True},
  }),
]
for name, payload in cases:
    pos=log_pos()
    try:
        body, dt = post(payload)
        usage=body.get("usage") or {}
        msg=(body.get("choices") or [{}])[0].get("message") or {}
        comp=int(usage.get("completion_tokens") or 0)
        row={
            "case": name, "ok": True, "seconds": round(dt,3),
            "completion_tokens": comp,
            "api_tok_s": round(comp/dt,2) if dt else None,
            "content_len": len(msg.get("content") or ""),
            "reasoning_len": len(msg.get("reasoning_content") or ""),
            "tool_calls": bool(msg.get("tool_calls")),
            "message_keys": list(msg.keys()),
        }
    except Exception as e:
        row={"case": name, "ok": False, "error": str(e)}
    time.sleep(0.3)
    row["server"]=scrape(pos)
    rows.append(row)
rec={"tag": tag, "model_id": (models.get("data") or [{}])[0].get("id"),
     "n_ctx": meta.get("n_ctx"), "size": meta.get("size"),
     "vram_after_load": g0, "vram_after_gen": gpu(), "cases": rows}
open(out,"w").write(json.dumps(rec, indent=2)+"\n")
print(json.dumps(rec, indent=2))
PY
}

trap restore_work EXIT
log "ornith trial start"
if [[ ! -f "$MODEL" ]]; then
  log "ERROR missing $MODEL"
  exit 1
fi
got="$(sha256sum "$MODEL" | awk '{print $1}')"
log "sha $got"
if [[ "$got" != "$EXPECT_SHA" ]]; then
  log "WARN sha mismatch expected $EXPECT_SHA"
fi

export ORNITH_MODEL="$MODEL"
sudo_cmd systemctl stop openclaw-qwen38-work-64k.service
for i in $(seq 1 40); do ss -ltn | grep -q ':18343 ' || break; sleep 1; done

ok=0
for spec in "200000:q4_0" "160000:q8_0" "128000:q4_0"; do
  export CTX="${spec%%:*}"
  export CTK="${spec##*:}"
  export CTV="$CTK"
  name="c${CTX}-${CTK}"
  if start_trial "$name"; then
    nvidia-smi --query-gpu=memory.used,memory.free,temperature.gpu --format=csv | tee -a "$LOG/trial-and-smoke.log"
    bench_protocol "$name" | tee -a "$LOG/trial-and-smoke.log" || log "WARN protocol bench failed"
    ok=1
    break
  fi
  log "load failed $name, trying smaller"
done
if [[ "$ok" -eq 0 ]]; then
  log "ERROR all ctx sizes failed"
  exit 1
fi

if [[ -x "$QCB_ROOT/scripts/run_suite.py" || -f "$QCB_ROOT/scripts/run_suite.py" ]]; then
  mkdir -p "$ROOT/qcb/results" "$ROOT/qcb/config"
  cat >"$ROOT/qcb/config/ornith-ad-q4k-iq4xs.toml" <<EOF
[model]
id = "ornith-1.5-35b-ad-q4k-iq4xs"
family = "Ornith-1.5-35B-A3B"
file = "$MODEL"
sha256 = "$got"
quantization = "AD-Q4_K-IQ4_XS"
template_id = "gguf-jinja"
notes = "AtomicChat AD-Q4_K-IQ4_XS; 4090 trial; do not replace WORK"

[endpoint]
base_url = "http://127.0.0.1:18343/v1"
model = "openclaw/Ornith-1.5-35B-EVAL"
api_key = "not-needed"
timeout_seconds = 900

[inference]
lane = "optimized"
temperature = 0.6
top_p = 0.95
top_k = 20
min_p = 0.0
seed = 42
max_tokens = 8192
context_size = ${CTX}
reasoning_effort = "medium"
mtp_enabled = false
tool_mode = true
max_tool_calls = 40
max_retries = 1
system_prompt_file = "config/system-prompt.txt"
extra_body = { chat_template_kwargs = { enable_thinking = true } }
EOF
  log "run QCB smoke 12x seed42"
  (cd "$QCB_ROOT" && PYTHONUNBUFFERED=1 python3 scripts/run_suite.py \
    --config "$ROOT/qcb/config/ornith-ad-q4k-iq4xs.toml" \
    --suite smoke --seeds 42 --resume \
    --output "$ROOT/qcb/results") | tee -a "$LOG/qcb-smoke.out" || log "WARN QCB smoke failed"
  jsonl="$ROOT/qcb/results/ornith-1.5-35b-ad-q4k-iq4xs-optimized-smoke.jsonl"
  if [[ -f "$jsonl" ]]; then
    python3 "$QCB_ROOT/scripts/generate_report.py" \
      --results "$jsonl" \
      --output "$ROOT/reports/ornith-smoke.md" \
      --json "$ROOT/reports/ornith-smoke.json" || true
  fi
else
  log "QCB runner not found, protocol smoke only"
fi
log "ornith trial done"
