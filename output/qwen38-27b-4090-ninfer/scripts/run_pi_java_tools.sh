#!/usr/bin/env bash
# Mac: NInfer Pi Java x3 + tools loop. Restore WORK on exit.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FIX="$ROOT/../../docs/qwen38-4090-vllm-extreme-v1.0/fixtures"
FIX="$(cd "$FIX" && pwd)"
PROXY="$ROOT/../qwen38-27b-4090-pi-ab/scripts/log_proxy.py"
export PATH="/Users/luo/.nvm/versions/node/v22.19.0/bin:$PATH"
export PI_CODING_AGENT_DIR="$ROOT/pi-config"
export PI_OFFLINE=1
export PI_SKIP_VERSION_CHECK=1
export PI_TELEMETRY=0
NOW() { date +%Y-%m-%dT%H:%M:%S; }
RES="$ROOT/results/pi-java"
WORK="$ROOT/work"
mkdir -p "$RES" "$WORK" "$ROOT/logs"

restore() {
  echo "RESTORE $(NOW)" | tee -a "$RES/status.txt"
  ssh -o ConnectTimeout=20 hhtele@192.168.10.29 'bash /tmp/4090_ninfer_stop_restore.sh' || true
  pkill -f "ssh .*18030:127.0.0.1:18030" 2>/dev/null || true
  pkill -f log_proxy.py 2>/dev/null || true
}
trap restore EXIT

echo "NINFER_PI_JAVA_START $(NOW)" | tee "$RES/status.txt"

scp -o ConnectTimeout=15 \
  "$ROOT/scripts/4090_ninfer_start.sh" \
  "$ROOT/scripts/4090_ninfer_stop_restore.sh" \
  hhtele@192.168.10.29:/tmp/
ssh -o ConnectTimeout=20 hhtele@192.168.10.29 'chmod +x /tmp/4090_ninfer_start.sh /tmp/4090_ninfer_stop_restore.sh; bash /tmp/4090_ninfer_start.sh'

pkill -f "ssh .*18030:127.0.0.1:18030" 2>/dev/null || true
ssh -f -N -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 \
  -L 127.0.0.1:18030:127.0.0.1:18030 hhtele@192.168.10.29
sleep 1
curl -fsS --max-time 5 http://127.0.0.1:18030/v1/models >/dev/null

pkill -f log_proxy.py 2>/dev/null || true
python3 "$PROXY" "$RES/proxy.jsonl" http://127.0.0.1:18030 \
  >"$RES/proxy.stdout" 2>"$RES/proxy.stderr" &
echo $! >"$RES/proxy.pid"
sleep 1

echo "===== tools HTTP smoke $(NOW) =====" | tee -a "$RES/status.txt"
python3 - <<'PY' | tee "$RES/tools-http.json"
import json, urllib.request
tools=[{"type":"function","function":{"name":"read_file","description":"Read a file","parameters":{"type":"object","properties":{"path":{"type":"string"}},"required":["path"]}}}]
body=json.dumps({
  "model":"qwen3.8-27b",
  "messages":[{"role":"user","content":"Call read_file on AGENTS.md and stop."}],
  "tools": tools, "tool_choice":"auto",
  "reasoning_effort":"none", "max_tokens":256,
}).encode()
req=urllib.request.Request("http://127.0.0.1:18444/v1/chat/completions", data=body, headers={"Content-Type":"application/json"}, method="POST")
with urllib.request.urlopen(req, timeout=180) as r:
    d=json.loads(r.read().decode())
msg=((d.get("choices") or [{}])[0].get("message") or {})
print(json.dumps({
  "finish": (d.get("choices") or [{}])[0].get("finish_reason"),
  "n_tools": len(msg.get("tool_calls") or []),
  "preview": (msg.get("content") or "")[:120],
  "tool": (msg.get("tool_calls") or [{}])[0].get("function",{}) if msg.get("tool_calls") else None,
  "pt": (d.get("usage") or {}).get("prompt_tokens"),
}, ensure_ascii=False))
PY

run_pi() {
  local name="$1" dir="$2" prompt="$3"
  local out="$RES/$name"
  mkdir -p "$out"
  echo "===== $name $(NOW) =====" | tee -a "$RES/status.txt"
  set +e
  (
    cd "$dir"
    perl -e 'alarm 1800; exec @ARGV' pi --print --mode json --no-session \
      --provider ninfer --model ninfer/qwen3.8-27b \
      --no-extensions --no-skills --thinking off --approve \
      --tools read,bash,edit,write,grep,find,ls \
      --session-dir "$out/sessions" --name "$name" \
      -- "$prompt"
  ) >"$out/pi.jsonl" 2>"$out/stderr.log"
  echo "pi_exit:$?" | tee -a "$out/stderr.log" | tee -a "$RES/status.txt"
  set -e
}

echo 'case,pi_exit,verify_exit,protected_ok,source_changed,elapsed_s' > "$RES/pi_cases.csv"

# tools loop on a copy of reconnect fixture (has logs/docs)
td="$WORK/tools-loop"
rm -rf "$td"
cp -a "$FIX/java-agent-3-reconnect-loop" "$td"
run_pi T-tools "$td" "$(cat "$ROOT/prompts/T-tools.txt")"

for src in "$FIX"/java-agent-*; do
  name=$(basename "$src")
  dst="$WORK/$name"
  rm -rf "$dst"
  cp -a "$src" "$dst"
  (
    cd "$dst"
    git init -q
    git config user.email bench@local
    git config user.name bench
    git add .
    git commit -qm baseline
  )
  before=$(cd "$dst" && { find src/test -type f; echo verify.sh; } | sort | xargs shasum -a 256 | shasum -a 256 | awk '{print $1}')
  start=$(date +%s)
  run_pi "$name" "$dst" "$(cat "$dst/TASK.md")"
  pirc=$(sed -n 's/^pi_exit://p' "$RES/$name/stderr.log" | tail -n 1)
  pirc=${pirc:-9}
  set +e
  (cd "$dst" && ./verify.sh) >"$RES/$name/verify.log" 2>&1
  vrc=$?
  set -e
  elapsed=$(( $(date +%s) - start ))
  after=$(cd "$dst" && { find src/test -type f; echo verify.sh; } | sort | xargs shasum -a 256 | shasum -a 256 | awk '{print $1}')
  protected=true
  [[ "$before" == "$after" ]] || protected=false
  changed=false
  (cd "$dst" && git diff --quiet -- src/main) || changed=true
  echo "$name,${pirc},$vrc,$protected,$changed,$elapsed" | tee -a "$RES/pi_cases.csv"
  (cd "$dst" && git diff -- src/main) >"$RES/$name/changes.patch" || true
  echo "[pi] $name pi=$pirc verify=$vrc protected=$protected changed=$changed elapsed=${elapsed}s" | tee -a "$RES/status.txt"
done

echo "NINFER_PI_JAVA_OK $(NOW)" | tee -a "$RES/status.txt"
cat "$RES/pi_cases.csv" | tee -a "$RES/status.txt"
