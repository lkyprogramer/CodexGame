#!/usr/bin/env bash
# Second pass: analogalok DFlash2 on PR #27342 binary, then Q4_K_M fallbacks.
# Does not replace boot WORK. EXIT restores WORK.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LAUNCH="$ROOT/launch"
LOG="$ROOT/logs"
PIDFILE="$LOG/eval.pid"
SUDO_PASS="${SUDO_PASS:-hhtele}"
mkdir -p "$LOG"

log() { echo "[$(date -u +%FT%TZ)] $*" | tee -a "$LOG/dflash2-retry.log"; }
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

start_script() {
  local script="$1" name="$2"
  stop_eval
  log "start $name CTX=${CTX:-} DRAFT=${DFLASH2_DRAFT:-} BIN=${LLAMA_SERVER_BIN:-default}"
  nohup "$script" >>"$LOG/eval-$name.out" 2>&1 &
  echo $! >"$PIDFILE"
  local i
  for i in $(seq 1 180); do
    if curl -sf --max-time 2 http://127.0.0.1:18343/v1/models | grep -q 'Qwen3.8-27B-EVAL'; then
      log "$name up (${i}s)"
      return 0
    fi
    if ! kill -0 "$(cat "$PIDFILE" 2>/dev/null || echo)" 2>/dev/null; then
      log "ERROR $name process died (${i}s)"
      tail -n 40 "$LOG/eval-$name.out" | tee -a "$LOG/dflash2-retry.log" || true
      return 1
    fi
    sleep 2
  done
  log "ERROR $name did not come up"
  tail -n 40 "$LOG/eval-$name.out" | tee -a "$LOG/dflash2-retry.log" || true
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

bench() {
  local tag="$1"
  local out="$LOG/bench-$tag.json"
  python3 - "$tag" "$out" <<'PY'
import json, time, urllib.request, sys, subprocess
tag, out = sys.argv[1], sys.argv[2]
def gpu():
    p=subprocess.check_output(["nvidia-smi","--query-gpu=memory.used,memory.free,temperature.gpu,power.draw","--format=csv,noheader,nounits"], text=True).strip()
    used,free,temp,pwr=[x.strip() for x in p.split(",")]
    return {"used_mib":float(used),"free_mib":float(free),"temp_c":float(temp),"power_w":float(pwr)}
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
payload={
  "model":"openclaw/Qwen3.8-27B-EVAL",
  "messages":[{"role":"user","content":"Write a Python function that returns the nth Fibonacci number. Code only."}],
  "max_tokens":256,
  "temperature":1.0,
  "chat_template_kwargs":{"enable_thinking":True,"reasoning_effort":"medium"},
}
body, dt = post(payload)
usage=body.get("usage") or {}
msg=(body.get("choices") or [{}])[0].get("message") or {}
comp=int(usage.get("completion_tokens") or 0)
tools_ok=False
try:
    tbody, tdt = post({
      "model":"openclaw/Qwen3.8-27B-EVAL",
      "messages":[{"role":"user","content":"Call the tool get_time with timezone UTC."}],
      "tools":[{"type":"function","function":{"name":"get_time","description":"current time","parameters":{"type":"object","properties":{"timezone":{"type":"string"}},"required":["timezone"]}}}],
      "max_tokens":256,
      "chat_template_kwargs":{"enable_thinking":True,"reasoning_effort":"low"},
    }, timeout=120)
    tmsg=(tbody.get("choices") or [{}])[0].get("message") or {}
    tools_ok=bool(tmsg.get("tool_calls"))
    tools_keys=list(tmsg.keys())
except Exception as e:
    tdt=None
    tools_keys=[str(e)]
g1=gpu()
rec={
  "tag": tag,
  "model_id": (models.get("data") or [{}])[0].get("id"),
  "n_ctx": meta.get("n_ctx"),
  "n_ctx_train": meta.get("n_ctx_train"),
  "size": meta.get("size"),
  "vram_after_load": g0,
  "vram_after_gen": g1,
  "fib_seconds": round(dt,2),
  "fib_completion_tokens": comp,
  "fib_tok_s": round(comp/dt,2) if dt else None,
  "fib_content_len": len(msg.get("content") or ""),
  "fib_reasoning_len": len(msg.get("reasoning_content") or ""),
  "tools_openai_tool_calls": tools_ok,
  "tools_seconds": tdt,
  "tools_message_keys": tools_keys,
}
open(out,"w").write(json.dumps(rec, indent=2)+"\n")
print(json.dumps(rec, indent=2))
PY
}

try_lane() {
  local script="$1" name="$2"
  if start_script "$script" "$name"; then
    nvidia-smi --query-gpu=memory.used,memory.free,temperature.gpu --format=csv | tee -a "$LOG/dflash2-retry.log"
    bench "$name" || log "WARN bench $name failed"
    return 0
  fi
  return 1
}

trap restore_work EXIT
log "dflash2-retry start"

sudo_cmd systemctl stop openclaw-qwen38-work-64k.service
for i in $(seq 1 40); do ss -ltn | grep -q ':18343 ' || break; sleep 1; done

ok=0
Q2=/data/models/qwen/qwen38/Qwen3.8-27B-DFlash2-Q2_K.gguf
Q4=/data/models/qwen/qwen38/Qwen3.8-27B-DFlash2-Q4_K_M.gguf
export LLAMA_SERVER_BIN=/home/hhtele/llama.cpp-qwen38-dflash2-pr27342/build/bin/llama-server

log "lane1 PR27342 + analogalok Q2_K"
export DFLASH2_DRAFT="$Q2"
for ctx in 250000 200000 170000; do
  export CTX="$ctx"
  if try_lane "$LAUNCH/production-alok-dflash2-pr27342.sh" "dflash2-pr27342-q2-c$ctx"; then
    ok=1
    break
  fi
  log "PR27342 Q2 -c $ctx failed, trying smaller"
done

if [[ "$ok" -eq 0 ]]; then
  log "lane2 PR27342 + Q4_K_M (same binary as 20260819 DFlash2 matrix)"
  export DFLASH2_DRAFT="$Q4"
  for ctx in 250000 200000 170000; do
    export CTX="$ctx"
    if try_lane "$LAUNCH/production-alok-dflash2-pr27342.sh" "dflash2-pr27342-q4-c$ctx"; then
      ok=1
      break
    fi
    log "PR27342 Q4 -c $ctx failed, trying smaller"
  done
fi

if [[ "$ok" -eq 0 ]]; then
  log "lane3 prod 20260817 + Q4_K_M"
  export LLAMA_SERVER_BIN=/home/hhtele/llama.cpp-qwen38-20260817/build/bin/llama-server
  export DFLASH2_Q2="$Q4"
  for ctx in 250000 200000 170000; do
    export CTX="$ctx"
    if try_lane "$LAUNCH/production-alok-dflash2.sh" "dflash2-prod-q4-c$ctx"; then
      ok=1
      break
    fi
    log "prod Q4 -c $ctx failed, trying smaller"
  done
fi

if [[ "$ok" -eq 0 ]]; then
  log "ERROR all DFlash2 lanes failed"
fi
log "dflash2-retry done"
