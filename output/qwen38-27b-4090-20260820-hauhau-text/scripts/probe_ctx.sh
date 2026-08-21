#!/usr/bin/env bash
# Try context/KV combos on :18443. Prints JSON lines. Does not restore WORK.
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WORKDIR="${HAUHAU_WORKDIR:-/home/hhtele/qwen38-hauhau-text-20260820}"
LOGDIR="$WORKDIR/logs"
OUT="$WORKDIR/results/probe.jsonl"
mkdir -p "$LOGDIR" "$WORKDIR/results"
: > "$OUT"

start_one() {
  local name="$1" ctx="$2" ctk="$3"
  pkill -f "llama-server.*--port 18443" >/dev/null 2>&1 || true
  sleep 2
  export TRIAL_PORT=18443 TRIAL_CTX="$ctx" TRIAL_CTK="$ctk" TRIAL_CTV="$ctk"
  nohup bash "$ROOT/launch/llama-text.sh" >"$LOGDIR/probe-${name}.stdout.log" 2>"$LOGDIR/probe-${name}.stderr.log" &
  echo $! >"$LOGDIR/probe-${name}.pid"
  local i
  for i in $(seq 1 90); do
    if ! kill -0 "$(cat "$LOGDIR/probe-${name}.pid")" 2>/dev/null; then
      echo "{\"name\":\"$name\",\"ok\":false,\"reason\":\"died\",\"ctx\":$ctx,\"ctk\":\"$ctk\"}" | tee -a "$OUT"
      tail -n 30 "$LOGDIR/probe-${name}.stderr.log" >&2 || true
      return 1
    fi
    if curl -fsS http://127.0.0.1:18443/v1/models >/dev/null 2>&1; then
      return 0
    fi
    sleep 2
  done
  echo "{\"name\":\"$name\",\"ok\":false,\"reason\":\"timeout\",\"ctx\":$ctx,\"ctk\":\"$ctk\"}" | tee -a "$OUT"
  kill "$(cat "$LOGDIR/probe-${name}.pid")" >/dev/null 2>&1 || true
  return 1
}

probe() {
  local name="$1" ctx="$2" ctk="$3"
  echo "=== probe $name ctx=$ctx kv=$ctk ==="
  if ! start_one "$name" "$ctx" "$ctk"; then
    return 1
  fi
  local vram
  vram="$(nvidia-smi --query-gpu=memory.used,memory.free --format=csv,noheader,nounits)"
  python3 - "$name" "$ctx" "$ctk" "$vram" "$OUT" <<'PY'
import json, sys, urllib.request, time
name, ctx, ctk, vram, outp = sys.argv[1:6]
used, free = [float(x.strip()) for x in vram.split(",")]
payload = {
  "model": "openclaw/Qwen3.8-27B-TEXT",
  "messages": [{"role":"user","content":"Write a long night-market paragraph and keep going."}],
  "max_tokens": 256,
  "temperature": 0.7,
  "top_p": 0.8,
  "chat_template_kwargs": {"enable_thinking": False, "reasoning_effort": "low", "preserve_thinking": False},
  "stream": False,
}
t0 = time.perf_counter()
ok = False
tps = None
err = None
try:
    req = urllib.request.Request("http://127.0.0.1:18443/v1/chat/completions", data=json.dumps(payload).encode(), headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(req, timeout=120) as res:
        body = json.loads(res.read().decode())
    elapsed = time.perf_counter() - t0
    timings = body.get("timings") or {}
    tps = timings.get("predicted_per_second")
    ok = True
except Exception as e:
    elapsed = time.perf_counter() - t0
    err = repr(e)
rec = {"name": name, "ok": ok, "ctx": int(ctx), "ctk": ctk, "vram_used_mib": used, "vram_free_mib": free, "fill256_tps": tps, "elapsed_s": elapsed, "error": err}
open(outp, "a").write(json.dumps(rec) + "\n")
print(json.dumps(rec), flush=True)
PY
  kill "$(cat "$LOGDIR/probe-${name}.pid")" >/dev/null 2>&1 || true
  sleep 2
}

# Large-first. q8 128K may OOM; q4 is the long-ctx path.
probe q8_128k 128000 q8_0 || true
probe q8_112k 112000 q8_0 || true
probe q4_192k 192000 q4_0 || true
probe q4_170k 170000 q4_0 || true
probe q4_160k 160000 q4_0 || true
probe q4_128k 128000 q4_0 || true

pkill -f "llama-server.*--port 18443" >/dev/null 2>&1 || true
echo "probe done"
