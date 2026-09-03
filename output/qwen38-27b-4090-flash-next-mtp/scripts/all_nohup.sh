#!/usr/bin/env bash
# One-shot: CUDA 12.3/sm_89 rebuild → F0/F1 bench → restore WORK.
# Intended: setsid nohup bash this-script </dev/null >logs/all.out 2>&1
set -uo pipefail
export PATH=/usr/local/cuda-12.3/bin:/usr/local/cuda/bin:/home/hhtele/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export CUDA_HOME=/usr/local/cuda-12.3
export LD_LIBRARY_PATH=/usr/local/cuda-12.3/lib64:/usr/local/cuda/lib64:${LD_LIBRARY_PATH:-}

ROOT="${ROOT:-/home/hhtele/qwen38-flash-next}"
SRC="${SRC:-/home/hhtele/llama.cpp-unsloth-src}"
WORKDIR="$ROOT"
WRAP="${SUDO_WRAP:-/home/hhtele/qwen38-dflash2-20260819/launch/sudo-wrap.sh}"
MODEL="${FLASH_NEXT_MODEL:-/data/models/qwen/flash-next-iq3xxs/Qwen3.8-Flash-Next-UD-IQ3_XXS-00001-of-00003.gguf}"
DRAFT="${FLASH_NEXT_DRAFT:-/data/models/qwen/flash-next-mtp/mtp-Qwen3.8-Flash-Next-shared-Q4_K_M.gguf}"
NCMOE="${NCMOE:-34}"

mkdir -p "$WORKDIR/logs" "$WORKDIR/results" "$WORKDIR/launch"
chmod +x "$WORKDIR"/launch/*.sh "$WORKDIR"/scripts/*.sh 2>/dev/null || true
exec >>"$WORKDIR/logs/all.out" 2>&1
echo "===== all_nohup start $(date -Is) pid=$$ ====="
echo "PATH=$PATH"
nvcc --version | tail -1 || true

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
      nvidia-smi --query-gpu=memory.used,memory.free --format=csv,noheader || true
      return 0
    fi
    sleep 2
  done
  echo "prod_restore_failed" >&2
  return 1
}

stop_prod() {
  echo "===== stop_prod $(date -Is) ====="
  if [[ -x "$WRAP" ]]; then
    "$WRAP" systemctl stop openclaw-qwen38-work-64k.service || true
  else
    sudo systemctl stop openclaw-qwen38-work-64k.service || true
  fi
  pkill -f "llama-server.*18443" 2>/dev/null || true
  sleep 3
  nvidia-smi --query-gpu=memory.used,memory.free --format=csv,noheader || true
}

trap 'echo "===== EXIT trap $(date -Is) status=$? ====="; restore_prod || true' EXIT

# --- unpack source if needed ---
if [[ ! -f "$SRC/CMakeLists.txt" ]]; then
  echo "unpack source"
  mkdir -p "$(dirname "$SRC")"
  tar -xzf /tmp/unsloth-llama-mtp-src.tgz -C "$(dirname "$SRC")"
  if [[ -d "$(dirname "$SRC")/llama.cpp" && "$(dirname "$SRC")/llama.cpp" != "$SRC" ]]; then
    rm -rf "$SRC"
    mv "$(dirname "$SRC")/llama.cpp" "$SRC"
  fi
fi
git -C "$SRC" log -1 --oneline || true

# --- build (WORK stays up) ---
echo "===== cmake $(date -Is) ====="
cmake -S "$SRC" -B "$SRC/build" \
  -DCMAKE_BUILD_TYPE=Release \
  -DGGML_CUDA=ON \
  -DGGML_NATIVE=ON \
  -DGGML_CUDA_FA=ON \
  -DCMAKE_CUDA_ARCHITECTURES=89 \
  -DCMAKE_CUDA_COMPILER=/usr/local/cuda-12.3/bin/nvcc
echo "===== build llama-server $(date -Is) ====="
cmake --build "$SRC/build" --target llama-server -j"$(nproc)"
BIN="$SRC/build/bin/llama-server"
export LD_LIBRARY_PATH="$SRC/build/bin:/usr/local/cuda-12.3/lib64:${LD_LIBRARY_PATH:-}"
"$BIN" --version | head -20
"$BIN" --help 2>&1 | grep -E "spec-type|n-cpu-moe|qwen" | head -20 || true
test -x "$BIN"
echo "BUILD_OK $BIN"

# point launch scripts at the new binary
sed -i "s|^BIN=.*|BIN=\"$BIN\"|" "$WORKDIR/launch/common.env" || true
# rewrite common.env BIN/LD
cat > "$WORKDIR/launch/common.env" <<EOF
export PATH=/usr/local/cuda-12.3/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export LD_LIBRARY_PATH=$SRC/build/bin:/usr/local/cuda-12.3/lib64:\${LD_LIBRARY_PATH:-}
BIN="$BIN"
MODEL="$MODEL"
DRAFT="$DRAFT"
WRAP="$WRAP"
EOF

wait_ready() {
  local pidfile="$1" logfile="$2"
  local pid
  pid=$(cat "$pidfile")
  local ready=0
  for i in $(seq 1 400); do
    if ! kill -0 "$pid" 2>/dev/null; then
      echo "server pid $pid died during wait"
      tail -n 120 "$logfile" || true
      return 1
    fi
    if curl -fsS http://127.0.0.1:18443/v1/models >/dev/null 2>&1; then
      echo "ready after ${i}s"
      return 0
    fi
    sleep 3
  done
  echo "not ready in 20min"
  tail -n 120 "$logfile" || true
  return 1
}

run_lane() {
  local lane="$1"
  shift
  echo "===== lane $lane $(date -Is) ====="
  pkill -f "llama-server.*18443" 2>/dev/null || true
  sleep 2
  nohup env LD_LIBRARY_PATH="$SRC/build/bin:/usr/local/cuda-12.3/lib64" "$@" \
    >"$WORKDIR/logs/${lane}.stdout.log" 2>"$WORKDIR/logs/${lane}.stderr.log" &
  echo $! >"$WORKDIR/logs/${lane}.pid"
  wait_ready "$WORKDIR/logs/${lane}.pid" "$WORKDIR/logs/${lane}.stderr.log"
  nvidia-smi --query-gpu=memory.used,memory.free --format=csv,noheader | tee "$WORKDIR/results/${lane}-vram.txt"
  grep -E "draft acceptance|offloaded|CPU MoE|n_cpu_moe|qwen4exp|spec-type" "$WORKDIR/logs/${lane}.stderr.log" | tail -n 30 || true
  python3 "$WORKDIR/scripts/bench_fill.py" --lane "$lane" --out "$WORKDIR/results/$lane"
  kill "$(cat "$WORKDIR/logs/${lane}.pid")" 2>/dev/null || true
  sleep 3
  pkill -f "llama-server.*18443" 2>/dev/null || true
  sleep 2
}

# --- eval (GPU exclusive) ---
stop_prod

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

echo "EVAL_OK $(date -Is)"
python3 - <<'PY'
import json
from pathlib import Path
root = Path("/home/hhtele/qwen38-flash-next/results")
print("===== summaries =====")
for lane in ("F0", "F1"):
    p = root / lane / "summary.json"
    print(lane, p.exists())
    if p.exists():
        print(p.read_text()[:2000])
PY
