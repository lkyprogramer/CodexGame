#!/usr/bin/env bash
# 200K ctx + DFLASH_SAMPLED_VERIFY on 18343. q8 first, q4 fallback. Trap restores WORK.
set -uo pipefail
export PATH=/usr/local/cuda-12.3/bin:/home/hhtele/bin:$PATH
ROOT=/home/hhtele/lucebox-qwen38-4090
BIN=$ROOT/server/build/dflash_server
IQ4=/data/models/qwen/qwen38-lucebox/Qwen3.8-27B-UD-IQ4_XS.gguf
Q8=/data/models/qwen/qwen38-lucebox/qwen38-dflash2-q8_0.gguf
WRAP=/home/hhtele/qwen38-dflash2-20260819/launch/sudo-wrap.sh
BENCH=$ROOT/scripts/bench_ctx_sampled.py
CTX=200000
OUT=$ROOT/results/ctx200k-sampled

mkdir -p "$ROOT/logs" "$OUT" "$ROOT/scripts"
exec >>"$ROOT/logs/ctx200k-sampled.out" 2>&1
echo "===== ctx200k-sampled start $(date -Is) pid=$$ ====="

restore_prod() {
  echo "===== restore_prod $(date -Is) ====="
  pkill -f "dflash_server" 2>/dev/null || true
  sleep 2
  if [[ -x "$WRAP" ]]; then
    "$WRAP" systemctl start openclaw-qwen38-work-64k.service || true
  else
    sudo systemctl start openclaw-qwen38-work-64k.service || true
  fi
  for i in $(seq 1 90); do
    if curl -fsS http://127.0.0.1:18343/v1/models >/dev/null 2>&1; then
      echo "prod_ready after ${i}s"
      return 0
    fi
    sleep 2
  done
  echo prod_restore_failed
  return 1
}
trap 'echo "===== EXIT trap $(date -Is) ====="; restore_prod || true' EXIT

test -x "$BIN"
test -s "$IQ4"
test -s "$Q8"
test -f "$BENCH"

if [[ -x "$WRAP" ]]; then
  "$WRAP" systemctl stop openclaw-qwen38-work-64k.service || true
else
  sudo systemctl stop openclaw-qwen38-work-64k.service || true
fi
pkill -f dflash_server 2>/dev/null || true
sleep 3

start_server() {
  local lane="$1" ck="$2" cv="$3"
  pkill -f dflash_server 2>/dev/null || true
  sleep 2
  echo "===== start $lane ctx=$CTX kv=$ck/$cv sampled_verify=1 $(date -Is) ====="
  nohup env DFLASH_SAMPLED_VERIFY=1 "$BIN" "$IQ4" \
    --draft "$Q8" \
    --target-device cuda:0 --draft-device cuda:0 \
    --draft-block-size 16 \
    --cache-type-k "$ck" --cache-type-v "$cv" \
    --max-ctx "$CTX" \
    --host 127.0.0.1 --port 18343 \
    --model-name qwen38-lucebox \
    >"$ROOT/logs/${lane}.stdout.log" 2>"$ROOT/logs/${lane}.stderr.log" &
  echo $! >"$ROOT/logs/${lane}.pid"
  for i in $(seq 1 120); do
    if curl -fsS http://127.0.0.1:18343/v1/models >/dev/null 2>&1; then
      echo "$lane ready ${i}s"
      nvidia-smi --query-gpu=memory.used,memory.free --format=csv,noheader | tee "$OUT/${lane}.vram.txt"
      rg -n "max_ctx|cache_type|ddtree|CUDA|out of memory|OOM" "$ROOT/logs/${lane}.stderr.log" | tail -n 40 || true
      return 0
    fi
    if ! kill -0 "$(cat "$ROOT/logs/${lane}.pid")" 2>/dev/null; then
      echo "$lane died"
      tail -n 80 "$ROOT/logs/${lane}.stderr.log"
      return 1
    fi
    sleep 2
  done
  echo "$lane not ready"
  tail -n 80 "$ROOT/logs/${lane}.stderr.log"
  return 1
}

probe_ok() {
  local lane="$1"
  python3 - <<PY
import json, urllib.request
body=json.dumps({
  "model":"qwen38-lucebox",
  "messages":[{"role":"user","content":"Write a Python merge_sorted(a, b). Code only."}],
  "max_tokens":64,
  "temperature":1.0,
  "top_p":0.95,
  "top_k":20,
  "chat_template_kwargs":{"enable_thinking":False},
}).encode()
req=urllib.request.Request("http://127.0.0.1:18343/v1/chat/completions", data=body, headers={"Content-Type":"application/json"}, method="POST")
try:
    with urllib.request.urlopen(req, timeout=120) as resp:
        d=json.loads(resp.read().decode())
except Exception as e:
    print("probe_error", e)
    raise SystemExit(1)
msg=((d.get("choices") or [{}])[0].get("message") or {})
content=(msg.get("content") or "").strip()
ct=(d.get("usage") or {}).get("completion_tokens")
print("probe_ct", ct, "empty", not bool(content), "preview", content[:80].replace("\n"," / "))
raise SystemExit(0 if content else 1)
PY
  local rc=$?
  if rg -q "cudaMalloc failed|out of memory" "$ROOT/logs/${lane}.stderr.log"; then
    echo "$lane probe OOM"
    return 1
  fi
  return "$rc"
}

LANE=""
# q8 200K already proven: idle boots, first decode cudaMalloc 2489MiB. Skip.
echo "skip C200Q8 (known idle-OK request-OOM)"
if start_server C200Q4 q4_0 q4_0 && probe_ok C200Q4; then
  LANE=C200Q4
fi

if [[ -z "$LANE" ]]; then
  echo "CTX200K_FAIL boot_or_probe"
  exit 1
fi
echo "USING_LANE=$LANE" | tee "$OUT/lane.txt"

python3 "$BENCH" http://127.0.0.1:18343 qwen38-lucebox "$CTX" "$OUT" \
  | tee "$OUT/${LANE}.jsonl"

echo "----- $LANE log markers -----"
rg -n "ar-decode|spec-decode|accept|max_ctx|out of memory|OOM|CUDA error" "$ROOT/logs/${LANE}.stderr.log" | tail -n 80 || true

if rg -q "cudaMalloc failed|out of memory" "$ROOT/logs/${LANE}.stderr.log"; then
  echo "CTX200K_FAIL oom_during_bench lane=$LANE"
  kill "$(cat "$ROOT/logs/${LANE}.pid")" 2>/dev/null || true
  sleep 2
  exit 1
fi
if ! rg -q "\[spec-decode\]" "$ROOT/logs/${LANE}.stderr.log"; then
  echo "CTX200K_FAIL no_spec_decode lane=$LANE"
  kill "$(cat "$ROOT/logs/${LANE}.pid")" 2>/dev/null || true
  sleep 2
  exit 1
fi

echo "CTX200K_OK lane=$LANE $(date -Is)"
nvidia-smi --query-gpu=memory.used,memory.free --format=csv,noheader || true
kill "$(cat "$ROOT/logs/${LANE}.pid")" 2>/dev/null || true
sleep 2
