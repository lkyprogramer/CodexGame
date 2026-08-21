#!/usr/bin/env bash
# Download is assumed complete. Probe, eval, install TEXT unit, restore WORK.
set -uo pipefail
WORKDIR="${HAUHAU_WORKDIR:-/home/hhtele/qwen38-hauhau-text-20260820}"
ROOT="$WORKDIR"
WRAP="${SUDO_WRAP:-/home/hhtele/qwen38-dflash2-20260819/launch/sudo-wrap.sh}"
MODEL="/data/models/qwen/qwen38-hauhau/Qwen3.8-27B-Uncensored-HauhauCS-Aggressive-Q4_K_P.gguf"
EXPECT_SHA="${EXPECT_SHA:-ba36dc3c2b2ff5e0aa5d71092a8894546996a6a119ae391803dda07cdc08516d}"
LOG="$WORKDIR/logs/run_deploy.log"
mkdir -p "$WORKDIR/logs" "$WORKDIR/results"
exec > >(tee -a "$LOG") 2>&1

restore_work() {
  echo "=== restore WORK $(date -Iseconds) ==="
  pkill -f "llama-server.*--port 18443" >/dev/null 2>&1 || true
  "$WRAP" systemctl stop openclaw-qwen38-text.service >/dev/null 2>&1 || true
  "$WRAP" systemctl start openclaw-qwen38-work-64k.service || echo WORK_START_FAIL
  for i in $(seq 1 90); do
    if curl -fsS http://127.0.0.1:18343/v1/models >/dev/null 2>&1; then
      echo "work_ready after ${i}s"
      curl -fsS http://127.0.0.1:18343/v1/models | python3 -c 'import sys,json; d=json.load(sys.stdin); x=d["data"][0]; print(x["id"], x.get("meta",{}).get("n_ctx"))'
      nvidia-smi --query-gpu=memory.used,memory.free --format=csv,noheader
      return 0
    fi
    sleep 2
  done
  echo "work_restore_failed" >&2
}
trap restore_work EXIT

echo "=== sha256 $(date -Iseconds) ==="
got="$(sha256sum "$MODEL" | awk '{print $1}')"
echo "got=$got expect=$EXPECT_SHA"
if [[ -n "$EXPECT_SHA" && "$got" != "$EXPECT_SHA" ]]; then
  echo "SHA mismatch" >&2
  exit 1
fi

echo "=== stop WORK $(date -Iseconds) ==="
"$WRAP" systemctl stop openclaw-qwen38-work-64k.service
sleep 2
nvidia-smi --query-gpu=memory.used,memory.free --format=csv,noheader

echo "=== probe $(date -Iseconds) ==="
bash "$ROOT/scripts/probe_ctx.sh"
python3 "$ROOT/scripts/pick_and_write_launch.py" \
  "$WORKDIR/results/probe.jsonl" \
  "$ROOT/launch/production-text-18343.sh" \
  "$ROOT/launch/llama-text.sh"
# copy chosen flags for eval on 18443
# shellcheck source=/dev/null
source "$ROOT/launch/common.env"
python3 - <<'PY'
import json
from pathlib import Path
ch = json.loads(Path("/home/hhtele/qwen38-hauhau-text-20260820/launch/chosen.json").read_text())["chosen"]
Path("/tmp/hauhau-chosen.env").write_text(f"export TRIAL_CTX={ch['ctx']}\nexport TRIAL_CTK={ch['ctk']}\nexport TRIAL_CTV={ch['ctk']}\nexport TRIAL_PORT=18443\n")
print(ch)
PY
# shellcheck source=/dev/null
source /tmp/hauhau-chosen.env

echo "=== eval server 18443 $(date -Iseconds) ==="
pkill -f "llama-server.*--port 18443" >/dev/null 2>&1 || true
nohup bash "$ROOT/launch/llama-text.sh" >"$WORKDIR/logs/eval.stdout.log" 2>"$WORKDIR/logs/eval.stderr.log" &
echo $! >"$WORKDIR/logs/eval.pid"
for i in $(seq 1 90); do
  if curl -fsS http://127.0.0.1:18443/v1/models >/dev/null 2>&1; then
    echo "eval ready $i"
    break
  fi
  sleep 2
done
long=0
python3 - <<'PY'
import json,os
from pathlib import Path
ch=json.loads(Path("/home/hhtele/qwen38-hauhau-text-20260820/launch/chosen.json").read_text())["chosen"]
print("LONG" if int(ch["ctx"])>=128000 else "SHORT")
PY
ctxflag="$(python3 -c 'import json;from pathlib import Path;ch=json.loads(Path("/home/hhtele/qwen38-hauhau-text-20260820/launch/chosen.json").read_text())["chosen"];print("yes" if int(ch["ctx"])>=128000 else "no")')"
extra=()
if [[ "$ctxflag" == yes ]]; then extra+=(--long-needles); fi
python3 "$ROOT/scripts/text_eval.py" \
  --base http://127.0.0.1:18443 \
  --model openclaw/Qwen3.8-27B-TEXT \
  --out "$WORKDIR/results/text-eval" \
  --skip-wait \
  "${extra[@]}"

kill "$(cat "$WORKDIR/logs/eval.pid")" >/dev/null 2>&1 || true
sleep 2

echo "=== install systemd TEXT (disabled) $(date -Iseconds) ==="
"$WRAP" mkdir -p /var/log/llama
"$WRAP" cp "$ROOT/launch/openclaw-qwen38-text.service" /etc/systemd/system/openclaw-qwen38-text.service
cat > /tmp/patch-work-conflicts.sh <<'EOS'
#!/bin/bash
set -e
p=/etc/systemd/system/openclaw-qwen38-work-64k.service
if grep -q 'openclaw-qwen38-text.service' "$p"; then
  echo WORK Conflicts already ok
  exit 0
fi
sed -i 's/Conflicts=openclaw-qwen36-mtp4-128k.service/Conflicts=openclaw-qwen36-mtp4-128k.service openclaw-qwen38-text.service/' "$p"
echo patched WORK Conflicts
EOS
"$WRAP" bash /tmp/patch-work-conflicts.sh
"$WRAP" systemctl daemon-reload
"$WRAP" systemctl disable openclaw-qwen38-text.service >/dev/null 2>&1 || true

echo "=== smoke TEXT on 18343 $(date -Iseconds) ==="
"$WRAP" systemctl start openclaw-qwen38-text.service
for i in $(seq 1 90); do
  if curl -fsS http://127.0.0.1:18343/v1/models >/dev/null 2>&1; then
    echo "text_smoke ready"
    curl -fsS http://127.0.0.1:18343/v1/models | python3 -c 'import sys,json; d=json.load(sys.stdin); x=d["data"][0]; print(x["id"], x.get("meta",{}).get("n_ctx"))'
    break
  fi
  sleep 2
done
"$WRAP" systemctl stop openclaw-qwen38-text.service
sleep 1
echo "=== deploy script done $(date -Iseconds) ==="
