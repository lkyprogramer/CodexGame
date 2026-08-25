#!/usr/bin/env bash
# After V3 + DFlash2 Q2 land: stop WORK, bench 200k MTP then analogalok DFlash2, restore WORK.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LAUNCH="$ROOT/launch"
LOG="$ROOT/logs"
PIDFILE="$LOG/eval.pid"
SUDO_PASS="${SUDO_PASS:-hhtele}"
V3=/data/models/qwen/qwen38/Qwen3.8-27B-UD-Q4_K_XL-dv3.gguf
Q2=/data/models/qwen/qwen38/Qwen3.8-27B-DFlash2-Q2_K.gguf
EXPECT_V3=3f227079003add2511437e5b1e94812e363385225bf6a9b47b0054a72bc8b01e
mkdir -p "$LOG"

log() { echo "[$(date -u +%FT%TZ)] $*" | tee -a "$LOG/trial-chain.log"; }
sudo_cmd() { echo "$SUDO_PASS" | sudo -S -p "" "$@"; }

wait_file() {
  local path="$1" name="$2"
  local i=0
  while [[ ! -f "$path" ]] || [[ -f "${path}.aria2" ]]; do
    if (( i % 30 == 0 )); then log "waiting $name"; fi
    sleep 10
    i=$((i+1))
    if (( i > 720 )); then log "ERROR timeout $name"; return 1; fi
  done
  log "have $name size=$(stat -c%s "$path")"
}

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
  log "start $name"
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
      tail -n 80 "$LOG/eval-$name.out" | tee -a "$LOG/trial-chain.log" || true
      return 1
    fi
    sleep 2
  done
  log "ERROR $name did not come up"
  tail -n 50 "$LOG/eval-$name.out" | tee -a "$LOG/trial-chain.log" || true
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
# short decode
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

trap restore_work EXIT
log "trial-chain start"
wait_file "$V3" "V3 gguf"
got="$(sha256sum "$V3" | awk '{print $1}')"
log "V3 sha $got expect $EXPECT_V3"
if [[ "$got" != "$EXPECT_V3" ]]; then
  log "WARN sha mismatch — still proceeding, record it"
fi
wait_file "$Q2" "DFlash2 Q2"

sudo_cmd systemctl stop openclaw-qwen38-work-64k.service
for i in $(seq 1 40); do ss -ltn | grep -q ':18343 ' || break; sleep 1; done

mtp_ok=0
for ctx in 200000 180000 170000; do
  export CTX="$ctx"
  if start_script "$LAUNCH/production-200k-mtp.sh" "mtp-c$ctx"; then
    nvidia-smi --query-gpu=memory.used,memory.free,temperature.gpu --format=csv | tee -a "$LOG/trial-chain.log"
    bench "mtp-c$ctx" || log "WARN bench mtp $ctx failed"
    mtp_ok=1
    break
  fi
  log "MTP -c $ctx failed to start, trying smaller"
done
if [[ "$mtp_ok" -eq 0 ]]; then
  log "ERROR all MTP ctx sizes failed"
fi

ok=0
for ctx in 250000 200000 170000; do
  export CTX="$ctx"
  if start_script "$LAUNCH/production-alok-dflash2.sh" "alok-dflash2-c$ctx"; then
    nvidia-smi --query-gpu=memory.used,memory.free,temperature.gpu --format=csv | tee -a "$LOG/trial-chain.log"
    bench "alok-dflash2-c$ctx" || log "WARN bench dflash2 $ctx failed"
    ok=1
    break
  fi
  log "DFlash2 -c $ctx failed to start, trying smaller"
done
if [[ "$ok" -eq 0 ]]; then
  log "ERROR all DFlash2 ctx sizes failed"
fi

log "trials done"
# EXIT restores WORK
