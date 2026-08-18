#!/usr/bin/env bash
set -euo pipefail

RUN_DIR="/home/hhtele/qwopus36-27b-v2-mtp-4090-20260525"
BUILD_DIR="/home/hhtele/llama.cpp-master-qwopus-20260525"
MODEL_DIR="/data/models/qwen/qwopus"
MODEL_FILE="Qwopus3.6-27B-v2-MTP-Q4_K_M.gguf"
MODEL_PATH="$MODEL_DIR/$MODEL_FILE"
MODEL_URL="https://hf-mirror.com/Jackrong/Qwopus3.6-27B-v2-MTP-GGUF/resolve/main/$MODEL_FILE"
EXPECTED_SIZE="16810713312"

mkdir -p "$RUN_DIR/logs" "$RUN_DIR/results" "$MODEL_DIR"
exec > >(tee -a "$RUN_DIR/logs/prepare.log") 2>&1

echo "PREPARE_START $(date -Is)"
echo "HOST $(hostname)"
echo "DISK"
df -h /data /home /tmp 2>/dev/null || true

download_model() {
  local size="0"
  if [[ -f "$MODEL_PATH" ]]; then
    size="$(stat -c '%s' "$MODEL_PATH")"
  fi
  if [[ "$size" == "$EXPECTED_SIZE" ]]; then
    echo "MODEL_ALREADY_PRESENT $MODEL_PATH $size"
    return
  fi
  echo "MODEL_DOWNLOAD_START $MODEL_URL"
  rm -f "$MODEL_PATH.aria2"
  aria2c -c -x 8 -s 8 -k 16M \
    -d "$MODEL_DIR" \
    -o "$MODEL_FILE" \
    "$MODEL_URL"
  size="$(stat -c '%s' "$MODEL_PATH")"
  echo "MODEL_SIZE $size"
  if [[ "$size" != "$EXPECTED_SIZE" ]]; then
    echo "MODEL_SIZE_MISMATCH expected=$EXPECTED_SIZE actual=$size" >&2
    exit 2
  fi
}

prepare_source() {
  if [[ -d "$BUILD_DIR/.git" ]]; then
    echo "LLAMA_SOURCE_EXISTING $BUILD_DIR"
    cd "$BUILD_DIR"
    git fetch --depth 1 origin master || echo "GIT_FETCH_FAILED_KEEP_EXISTING"
    git checkout master || true
    git pull --ff-only || echo "GIT_PULL_FAILED_KEEP_EXISTING"
  else
    echo "LLAMA_SOURCE_CLONE $BUILD_DIR"
    timeout 180 git clone --depth 1 https://github.com/ggml-org/llama.cpp.git "$BUILD_DIR"
    cd "$BUILD_DIR"
  fi
  echo "LLAMA_COMMIT $(git rev-parse HEAD)"
}

build_llama() {
  cd "$BUILD_DIR"
  cmake -S . -B build \
    -DBUILD_SHARED_LIBS=OFF \
    -DLLAMA_BUILD_UI=OFF \
    -DLLAMA_BUILD_WEBUI=OFF \
    -DGGML_CUDA=ON \
    -DGGML_CUDA_FA=ON \
    -DGGML_CUDA_GRAPHS=ON \
    -DCMAKE_CUDA_COMPILER=/usr/local/cuda/bin/nvcc \
    -DCMAKE_CUDA_ARCHITECTURES=89 \
    -DCMAKE_BUILD_TYPE=Release
  cmake --build build --config Release -j --target llama-server llama-cli
  build/bin/llama-server --version | tee "$RUN_DIR/logs/llama-server-version.txt"
  build/bin/llama-server --help 2>&1 | tee "$RUN_DIR/logs/llama-server-help.txt" >/dev/null
  grep -E -- 'spec-type|spec-draft|cache-prompt|chat-template|ctx' "$RUN_DIR/logs/llama-server-help.txt" \
    | tee "$RUN_DIR/logs/llama-server-help-filtered.txt"
}

download_model
prepare_source
build_llama
echo "PREPARE_DONE $(date -Is)"
