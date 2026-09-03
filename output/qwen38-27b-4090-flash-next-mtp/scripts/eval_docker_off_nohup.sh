#!/usr/bin/env bash
# Stop Docker + WORK, F0/F1 with load-mode none and real decode, restore both.
set -uo pipefail
export PATH=/usr/local/cuda-12.3/bin:/home/hhtele/bin:/usr/sbin:/usr/bin:/sbin:/bin
export LD_LIBRARY_PATH=/home/hhtele/llama.cpp-unsloth-src/build/bin:/usr/local/cuda-12.3/lib64:${LD_LIBRARY_PATH:-}

ROOT=/home/hhtele/qwen38-flash-next
SRC=/home/hhtele/llama.cpp-unsloth-src
BIN="$SRC/build/bin/llama-server"
MODEL=/data/models/qwen/flash-next-iq3xxs/Qwen3.8-Flash-Next-UD-IQ3_XXS-00001-of-00003.gguf
DRAFT=/data/models/qwen/flash-next-mtp/mtp-Qwen3.8-Flash-Next-shared-Q4_K_M.gguf
WRAP=/home/hhtele/qwen38-dflash2-20260819/launch/sudo-wrap.sh
NCMOE=34
DOCKER_LIST=$ROOT/logs/docker-stopped.names

mkdir -p "$ROOT/logs" "$ROOT/results"
exec >>"$ROOT/logs/eval-docker-off.out" 2>&1
echo "===== eval_docker_off start $(date -Is) pid=$$ ====="
free -h | head -2
nvidia-smi --query-gpu=memory.used,memory.free --format=csv,noheader || true

restore_docker() {
  echo "===== restore_docker $(date -Is) ====="
  if [[ -f "$DOCKER_LIST" ]]; then
    # postgres/redis/minio first
    for n in cipherlink-redis cipherlink-postgres cipherlink-minio cipherlink-gateway cipherlink-backend \
             exam-management onnxocr-ppocrv6-small-cpu-compat vault-transit-test old-hand-verify fervent_moore; do
      grep -qx "$n" "$DOCKER_LIST" && docker start "$n" || true
    done
    while read -r n; do
      [[ -z "$n" ]] && continue
      docker start "$n" >/dev/null 2>&1 || true
    done < "$DOCKER_LIST"
  fi
  docker ps --format "{{.Names}}" || true
}

restore_prod() {
  echo "===== restore_prod $(date -Is) ====="
  pkill -f "llama-server.*18443" 2>/dev/null || true
  sleep 2
  if [[ -x "$WRAP" ]]; then
    "$WRAP" systemctl start openclaw-qwen38-work-64k.service || true
  else
    sudo systemctl start openclaw-qwen38-work-64k.service || true
  fi
  for i in $(seq 1 90); do
    if curl -fsS http://127.0.0.1:18343/v1/models >/dev/null 2>&1; then
      echo "prod_ready after ${i}s"
      curl -fsS http://127.0.0.1:18343/v1/models || true
      return 0
    fi
    sleep 2
  done
  echo "prod_restore_failed" >&2
  return 1
}

trap 'echo "===== EXIT trap $(date -Is) status=$? ====="; restore_prod || true; restore_docker || true; free -h | head -2' EXIT

test -x "$BIN"
test -f "$MODEL"
test -f "$DRAFT"

echo "===== stop docker $(date -Is) ====="
docker ps --format "{{.Names}}" | tee "$DOCKER_LIST"
# stop non-infra first, then db
docker stop exam-management onnxocr-ppocrv6-small-cpu-compat cipherlink-backend cipherlink-gateway \
  vault-transit-test old-hand-verify fervent_moore cipherlink-minio cipherlink-postgres cipherlink-redis \
  2>/dev/null || true
# any leftover from the list
while read -r n; do
  docker stop "$n" >/dev/null 2>&1 || true
done < "$DOCKER_LIST"
sleep 2
echo "===== after docker stop ====="
docker ps --format "{{.Names}}" || true
free -h | head -2
# drop caches if possible (needs root); ignore failure
if [[ -x "$WRAP" ]]; then
  "$WRAP" sh -c 'sync; echo 3 > /proc/sys/vm/drop_caches' 2>/dev/null || true
fi
free -h | head -2

echo "===== stop WORK $(date -Is) ====="
if [[ -x "$WRAP" ]]; then
  "$WRAP" systemctl stop openclaw-qwen38-work-64k.service || true
else
  sudo systemctl stop openclaw-qwen38-work-64k.service || true
fi
pkill -f "llama-server.*18443" 2>/dev/null || true
sleep 3
nvidia-smi --query-gpu=memory.used,memory.free --format=csv,noheader || true
free -h | head -2

wait_ready() {
  local pidfile="$1" logfile="$2"
  local pid
  pid=$(cat "$pidfile")
  for i in $(seq 1 400); do
    if ! kill -0 "$pid" 2>/dev/null; then
      echo "server died"
      tail -n 80 "$logfile" || true
      return 1
    fi
    if curl -fsS http://127.0.0.1:18443/v1/models >/dev/null 2>&1; then
      echo "ready after ${i}s"
      return 0
    fi
    sleep 3
  done
  echo "not ready"
  tail -n 80 "$logfile" || true
  return 1
}

run_lane() {
  local lane="$1"
  shift
  echo "===== lane $lane $(date -Is) ====="
  pkill -f "llama-server.*18443" 2>/dev/null || true
  sleep 2
  nohup env LD_LIBRARY_PATH="$SRC/build/bin:/usr/local/cuda-12.3/lib64" "$@" \
    >"$ROOT/logs/${lane}-clean.stdout.log" 2>"$ROOT/logs/${lane}-clean.stderr.log" &
  echo $! >"$ROOT/logs/${lane}-clean.pid"
  wait_ready "$ROOT/logs/${lane}-clean.pid" "$ROOT/logs/${lane}-clean.stderr.log"
  nvidia-smi --query-gpu=memory.used,memory.free --format=csv,noheader | tee "$ROOT/results/${lane}-clean-vram.txt"
  free -h | head -2
  python3 "$ROOT/scripts/bench_fill.py" --lane "${lane}-clean" --out "$ROOT/results/${lane}-clean"
  grep -E "eval time|prompt eval time|draft acceptance" "$ROOT/logs/${lane}-clean.stderr.log" | tail -n 20 || true
  kill "$(cat "$ROOT/logs/${lane}-clean.pid")" 2>/dev/null || true
  sleep 3
  pkill -f "llama-server.*18443" 2>/dev/null || true
  sleep 2
}

COMMON=(
  "$BIN"
  -m "$MODEL"
  --alias qwen38-flash-next
  --host 127.0.0.1 --port 18443
  -ngl 999 --n-cpu-moe "$NCMOE"
  -c 65536 -np 1 -fa on --jinja --no-mmproj
  --cache-type-k q8_0 --cache-type-v q8_0
  -t 12 --metrics --predict 2048
)

run_lane F0 "${COMMON[@]}" --spec-type none
run_lane F1 "${COMMON[@]}" -md "$DRAFT" --spec-type draft-mtp --spec-draft-n-max 3

echo "EVAL_CLEAN_OK $(date -Is)"
for lane in F0-clean F1-clean; do
  echo "===== $lane summary ====="
  cat "$ROOT/results/$lane/summary.json" 2>/dev/null || true
done
