#!/usr/bin/env bash
set -euo pipefail

ROOT=/home/hhtele/llama.cpp-turboquant-pr146-20260518
RUN_DIR=/home/hhtele/qwen36-turboquant-pr146-20260518
LOG_DIR="$RUN_DIR/logs"
mkdir -p "$LOG_DIR"

export PATH=/usr/local/cuda/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export LD_LIBRARY_PATH=/usr/local/cuda/lib64:${LD_LIBRARY_PATH:-}
export CUDACXX=/usr/local/cuda/bin/nvcc

if [ ! -d "$ROOT/.git" ]; then
  git clone https://github.com/TheTom/llama-cpp-turboquant.git "$ROOT"
fi

git -C "$ROOT" fetch origin pull/146/head:pr146-sync-upstream-b9190-mtp
git -C "$ROOT" checkout -f pr146-sync-upstream-b9190-mtp

{
  echo "COMMIT $(git -C "$ROOT" rev-parse --short HEAD)"
  echo "BRANCH $(git -C "$ROOT" rev-parse --abbrev-ref HEAD)"
  echo "DATE $(date -Is)"
  cmake -S "$ROOT" -B "$ROOT/build" \
    -DBUILD_SHARED_LIBS=OFF \
    -DLLAMA_BUILD_UI=OFF \
    -DLLAMA_BUILD_WEBUI=OFF \
    -DGGML_CUDA=ON \
    -DGGML_CUDA_FA=ON \
    -DGGML_CUDA_GRAPHS=ON \
    -DCMAKE_CUDA_COMPILER=/usr/local/cuda/bin/nvcc \
    -DCMAKE_CUDA_ARCHITECTURES=89 \
    -DCMAKE_BUILD_TYPE=Release
  cmake --build "$ROOT/build" --config Release -j "$(nproc)" --target llama-server
  "$ROOT/build/bin/llama-server" --version
  "$ROOT/build/bin/llama-server" --help > "$LOG_DIR/llama-server-help.txt" 2>&1
  grep -E -- 'draft-mtp|spec-draft-p-min|spec-type|cache-type-k|cache-type-v|turbo2|turbo3|turbo4|cache-ram' \
    "$LOG_DIR/llama-server-help.txt" > "$LOG_DIR/llama-server-help-filtered.txt" || true
  echo "HELP_CHECK_DRAFT_MTP=$(grep -c -- 'draft-mtp' "$LOG_DIR/llama-server-help.txt" || true)"
  echo "HELP_CHECK_TURBO2=$(grep -c -- 'turbo2' "$LOG_DIR/llama-server-help.txt" || true)"
  echo "HELP_CHECK_TURBO3=$(grep -c -- 'turbo3' "$LOG_DIR/llama-server-help.txt" || true)"
  echo "HELP_CHECK_TURBO4=$(grep -c -- 'turbo4' "$LOG_DIR/llama-server-help.txt" || true)"
} 2>&1 | tee "$LOG_DIR/build.log"

