#!/usr/bin/env bash
# Wait compile+downloads, convert DFlash2 Q8, stop WORK, serve 18343, bench_lane, restore.
set -uo pipefail
export PATH=/usr/local/cuda-12.3/bin:/home/hhtele/bin:/usr/sbin:/usr/bin:/sbin:/bin
ROOT=/home/hhtele/lucebox-qwen38-4090
IQ4=/data/models/qwen/qwen38-lucebox/Qwen3.8-27B-UD-IQ4_XS.gguf
IQ4_WANT=14252845984
ST=/data/models/qwen/qwen38-dflash2-src/model.safetensors
ST_WANT=3848817896
F16=/data/models/qwen/qwen38-lucebox/qwen38-dflash2-f16.gguf
Q8=/data/models/qwen/qwen38-lucebox/qwen38-dflash2-q8_0.gguf
BIN=$ROOT/server/build/dflash_server
WRAP=/home/hhtele/qwen38-dflash2-20260819/launch/sudo-wrap.sh
BENCH=/home/hhtele/qwen38-buun-20260901/scripts/bench_lane.py
UV=/home/hhtele/bin/uv
PY="$UV run --python 3.12 --with numpy python"

mkdir -p "$ROOT/logs" "$ROOT/results/smoke"
exec >>"$ROOT/logs/wait-smoke.out" 2>&1
echo "===== wait_build_smoke start $(date -Is) pid=$$ ====="

wait_file() {
  local f="$1" want="$2" name="$3"
  for i in $(seq 1 240); do
    if [[ -f "$f" && ! -f "${f}.aria2" ]]; then
      local sz
      sz=$(stat -c%s "$f")
      echo "$name size=$sz want=$want"
      [[ "$sz" -eq "$want" ]] && return 0
    fi
    echo "waiting $name $i $(date +%H:%M:%S)"
    sleep 15
  done
  echo "TIMEOUT $name"
  return 1
}

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
  echo "prod_restore_failed"
  return 1
}

# compile may still be running; trap only after we stop WORK
wait_file "$IQ4" "$IQ4_WANT" IQ4 || exit 1
wait_file "$ST" "$ST_WANT" DFLASH2 || exit 1

if [[ -x "$BIN" ]]; then
  echo BUILD_READY existing_binary
else
  for i in $(seq 1 240); do
    if grep -q BUILD_OK "$ROOT/logs/compile.out" 2>/dev/null && [[ -x "$BIN" ]]; then
      echo BUILD_READY
      break
    fi
    if [[ -x "$BIN" ]]; then
      echo BUILD_READY binary_without_marker
      break
    fi
    if ! pgrep -f "logs/compile.sh" >/dev/null && ! grep -q BUILD_OK "$ROOT/logs/compile.out" 2>/dev/null; then
      echo COMPILE_DIED
      tail -n 80 "$ROOT/logs/compile.out"
      exit 1
    fi
    echo "waiting compile $i $(date +%H:%M:%S)"
    sleep 15
  done
fi
test -x "$BIN"

if [[ ! -s "$Q8" ]]; then
  echo "===== convert draft $(date -Is) ====="
  cd "$ROOT/server"
  PYTHONPATH="$ROOT/server/deps/llama.cpp/gguf-py:${PYTHONPATH:-}" \
    $PY scripts/convert_dflash_to_gguf.py "$ST" "$F16" --no-aux-heads
  PYTHONPATH="$ROOT/server/deps/llama.cpp/gguf-py:${PYTHONPATH:-}" \
    $PY scripts/quantize_dflash_draft.py "$F16" "$Q8" --scheme q8_0
  ls -lh "$F16" "$Q8"
fi

trap 'echo "===== EXIT trap $(date -Is) ====="; restore_prod || true' EXIT

echo "===== stop WORK $(date -Is) ====="
if [[ -x "$WRAP" ]]; then
  "$WRAP" systemctl stop openclaw-qwen38-work-64k.service || true
else
  sudo systemctl stop openclaw-qwen38-work-64k.service || true
fi
pkill -f "dflash_server" 2>/dev/null || true
sleep 3

echo "===== start dflash_server :18343 $(date -Is) ====="
nohup "$BIN" "$IQ4" \
  --draft "$Q8" \
  --target-device cuda:0 --draft-device cuda:0 \
  --draft-block-size 16 \
  --cache-type-k q8_0 --cache-type-v q8_0 \
  --max-ctx 32768 \
  --host 127.0.0.1 --port 18343 \
  --model-name qwen38-lucebox \
  >"$ROOT/logs/server.stdout.log" 2>"$ROOT/logs/server.stderr.log" &
echo $! >"$ROOT/logs/server.pid"

ready=0
for i in $(seq 1 180); do
  if curl -fsS http://127.0.0.1:18343/health >/dev/null 2>&1 \
     || curl -fsS http://127.0.0.1:18343/v1/models >/dev/null 2>&1; then
    ready=1
    echo "server ready ${i}s"
    break
  fi
  if ! kill -0 "$(cat "$ROOT/logs/server.pid")" 2>/dev/null; then
    echo "server died"
    tail -n 80 "$ROOT/logs/server.stderr.log"
    exit 1
  fi
  sleep 2
done
[[ "$ready" == 1 ]] || { echo not_ready; tail -n 80 "$ROOT/logs/server.stderr.log"; exit 1; }

curl -fsS http://127.0.0.1:18343/v1/models | tee "$ROOT/results/smoke/models.json" || true
nvidia-smi --query-gpu=memory.used,memory.free --format=csv,noheader | tee "$ROOT/results/smoke/vram.txt"

python3 "$BENCH" --base http://127.0.0.1:18343 --model qwen38-lucebox \
  --lane lucebox-smoke --out "$ROOT/results/smoke" --skip-wait

echo "SMOKE_OK $(date -Is)"
python3 - <<'PY'
import json
from pathlib import Path
p=Path("/home/hhtele/lucebox-qwen38-4090/results/smoke/summary.json")
print(p.read_text()[:5000] if p.exists() else "no summary")
PY
kill "$(cat "$ROOT/logs/server.pid")" 2>/dev/null || true
sleep 2
