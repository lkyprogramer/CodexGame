#!/usr/bin/env bash
# Scan MTP n-max 1/2/3/4 on live V3 200K q4. Restores WORK n=2 on EXIT.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LAUNCH="$ROOT/launch"
LOG="$ROOT/logs"
PIDFILE="$LOG/eval.pid"
SUDO_PASS="${SUDO_PASS:-hhtele}"
mkdir -p "$LOG"

log() { echo "[$(date -u +%FT%TZ)] $*" | tee -a "$LOG/mtp-n-scan.log"; }
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

start_n() {
  local n="$1"
  stop_eval
  export SPEC_N="$n"
  log "start mtp n=$n"
  nohup "$LAUNCH/production-mtp-n.sh" >>"$LOG/eval-mtp-n$n.out" 2>&1 &
  echo $! >"$PIDFILE"
  local i
  for i in $(seq 1 90); do
    if curl -sf --max-time 2 http://127.0.0.1:18343/v1/models | grep -q 'Qwen3.8-27B-EVAL'; then
      log "n=$n up (${i}s)"
      return 0
    fi
    if ! kill -0 "$(cat "$PIDFILE" 2>/dev/null || echo)" 2>/dev/null; then
      log "ERROR n=$n died"
      tail -n 30 "$LOG/eval-mtp-n$n.out" | tee -a "$LOG/mtp-n-scan.log" || true
      return 1
    fi
    sleep 2
  done
  log "ERROR n=$n did not come up"
  return 1
}

restore_work() {
  log "restore WORK n=2"
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

bench() {
  local n="$1"
  local slog="$LOG/eval-mtp-n$n.out"
  python3 - "$n" "$LOG/bench-mtp-n$n.json" "$slog" <<'PY'
import json, time, urllib.request, sys, subprocess, re
n, out, slog = sys.argv[1], sys.argv[2], sys.argv[3]

def gpu():
    p=subprocess.check_output(
        ["nvidia-smi","--query-gpu=memory.used,memory.free,temperature.gpu,power.draw",
         "--format=csv,noheader,nounits"], text=True).strip()
    used,free,temp,pwr=[x.strip() for x in p.split(",")]
    return {"used_mib":float(used),"free_mib":float(free),"temp_c":float(temp),"power_w":float(pwr)}

def log_pos():
    try:
        return open(slog,"rb").seek(0,2)
    except FileNotFoundError:
        return 0

def scrape(pos):
    rec={"eval_tok_s":None,"acceptance":None,"accepted":None,"generated":None,"mean_len":None,"prompt_tok_s":None}
    try:
        with open(slog,"rb") as f:
            f.seek(pos)
            text=f.read().decode("utf-8","replace")
    except FileNotFoundError:
        return rec
    ev=re.findall(r"eval time =\s+[\d.]+ ms /\s+(\d+) tokens \(\s*[\d.]+ ms per token,\s+([\d.]+) tokens per second\)", text)
    pr=re.findall(r"prompt eval time =\s+[\d.]+ ms /\s+(\d+) tokens \(\s*[\d.]+ ms per token,\s+([\d.]+) tokens per second\)", text)
    ac=re.findall(r"draft acceptance =\s+([\d.]+) \(\s*(\d+) accepted /\s+(\d+) generated\), mean len =\s+([\d.]+)", text)
    if ev:
        rec["eval_tokens"]=int(ev[-1][0]); rec["eval_tok_s"]=float(ev[-1][1])
    if pr:
        rec["prompt_tokens"]=int(pr[-1][0]); rec["prompt_tok_s"]=float(pr[-1][1])
    if ac:
        rec["acceptance"]=float(ac[-1][0]); rec["accepted"]=int(ac[-1][1])
        rec["generated"]=int(ac[-1][2]); rec["mean_len"]=float(ac[-1][3])
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
    "model":"openclaw/Qwen3.8-27B-EVAL",
    "messages":[{"role":"user","content":"Write a Python function that returns the nth Fibonacci number. Code only."}],
    "max_tokens":256,
    "temperature":1.0,
    "chat_template_kwargs":{"enable_thinking":True,"reasoning_effort":"medium"},
  }),
  ("tools", {
    "model":"openclaw/Qwen3.8-27B-EVAL",
    "messages":[{"role":"user","content":"Call the tool get_time with timezone UTC."}],
    "tools":[{"type":"function","function":{"name":"get_time","description":"current time","parameters":{"type":"object","properties":{"timezone":{"type":"string"}},"required":["timezone"]}}}],
    "max_tokens":256,
    "chat_template_kwargs":{"enable_thinking":True,"reasoning_effort":"low"},
  }),
  ("think", {
    "model":"openclaw/Qwen3.8-27B-EVAL",
    "messages":[{"role":"user","content":"Explain step by step how a concurrent LRU cache with TTL should handle expired entries under contention. Be thorough, then give a short conclusion."}],
    "max_tokens":512,
    "temperature":1.0,
    "chat_template_kwargs":{"enable_thinking":True,"reasoning_effort":"medium"},
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
            "case": name,
            "ok": True,
            "seconds": round(dt,3),
            "completion_tokens": comp,
            "api_tok_s": round(comp/dt,2) if dt else None,
            "content_len": len(msg.get("content") or ""),
            "reasoning_len": len(msg.get("reasoning_content") or ""),
            "tool_calls": bool(msg.get("tool_calls")),
            "message_keys": list(msg.keys()),
        }
    except Exception as e:
        row={"case": name, "ok": False, "error": str(e)}
        dt=None
    time.sleep(0.3)
    row["server"]=scrape(pos)
    rows.append(row)

g1=gpu()
rec={
  "n": int(n),
  "model_id": (models.get("data") or [{}])[0].get("id"),
  "n_ctx": meta.get("n_ctx"),
  "vram_after_load": g0,
  "vram_after_gen": g1,
  "cases": rows,
}
open(out,"w").write(json.dumps(rec, indent=2)+"\n")
print(json.dumps(rec, indent=2))
PY
}

trap restore_work EXIT
log "mtp-n-scan start"
sudo_cmd systemctl stop openclaw-qwen38-work-64k.service
for i in $(seq 1 40); do ss -ltn | grep -q ':18343 ' || break; sleep 1; done

ok=0
for n in 1 2 3 4; do
  if start_n "$n"; then
    nvidia-smi --query-gpu=memory.used,memory.free,temperature.gpu --format=csv | tee -a "$LOG/mtp-n-scan.log"
    bench "$n" | tee -a "$LOG/mtp-n-scan.log" || log "WARN bench n=$n failed"
    ok=1
  else
    log "skip bench n=$n"
  fi
done
if [[ "$ok" -eq 0 ]]; then
  log "ERROR no n came up"
fi
log "mtp-n-scan done"
