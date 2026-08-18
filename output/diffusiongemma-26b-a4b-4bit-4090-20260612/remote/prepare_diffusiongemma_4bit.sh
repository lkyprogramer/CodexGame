#!/usr/bin/env bash
set -euo pipefail

RUN_DIR="/home/hhtele/diffusiongemma-26b-a4b-4bit-4090-20260612"
LOG_DIR="$RUN_DIR/logs"
MODEL_DIR="/data/models/gemma/diffusiongemma"
MODEL_FILE="diffusiongemma-26B-A4B-it-Q4_K_M.gguf"
MODEL_PATH="$MODEL_DIR/$MODEL_FILE"
MODEL_URL="https://hf-mirror.com/unsloth/diffusiongemma-26B-A4B-it-GGUF/resolve/main/$MODEL_FILE"
EXPECTED_SIZE="16806810336"
SRC_DIR="/home/hhtele/llama.cpp-diffusiongemma-pr24423-20260612"
SOURCE_TARBALL="$RUN_DIR/llama-cpp-pr24423.tar.gz"
SOURCE_SHA_FILE="$RUN_DIR/llama-cpp-pr24423.sha"

mkdir -p "$RUN_DIR" "$LOG_DIR"
if [[ ! -d "$MODEL_DIR" ]]; then
  printf 'hhtele\n' | sudo -S mkdir -p "$MODEL_DIR"
  printf 'hhtele\n' | sudo -S chown -R "$USER:$USER" /data/models/gemma
fi
exec > >(tee -a "$LOG_DIR/prepare.log") 2>&1

echo "PREPARE_START $(date -Is)"
echo "RUN_DIR $RUN_DIR"
echo "MODEL_PATH $MODEL_PATH"
echo "SRC_DIR $SRC_DIR"

echo "REMOTE_ENV"
hostname
date -Is
df -h /data /home || true
command -v aria2c
command -v git
command -v cmake
nvidia-smi --query-gpu=name,driver_version,memory.total,memory.used,memory.free --format=csv,noheader,nounits || true

echo "RANGE_CHECK"
curl -LIs --max-time 30 "$MODEL_URL" | tr -d '\r' | egrep -i 'HTTP/|content-length|accept-ranges|location|x-linked-size' || true

if [[ -f "$MODEL_PATH" ]]; then
  size="$(stat -c '%s' "$MODEL_PATH")"
  if [[ "$size" == "$EXPECTED_SIZE" ]]; then
    echo "MODEL_EXISTS_OK $size"
  else
    echo "MODEL_EXISTS_BAD_SIZE $size expected=$EXPECTED_SIZE"
    rm -f "$MODEL_PATH"
  fi
fi

if [[ ! -f "$MODEL_PATH" ]]; then
  aria2c -c -x 8 -s 8 -k 16M \
    -d "$MODEL_DIR" \
    -o "$MODEL_FILE" \
    "$MODEL_URL"
fi

size="$(stat -c '%s' "$MODEL_PATH")"
echo "MODEL_SIZE $size"
if [[ "$size" != "$EXPECTED_SIZE" ]]; then
  echo "MODEL_SIZE_MISMATCH expected=$EXPECTED_SIZE actual=$size"
  exit 21
fi

if [[ -f "$SOURCE_TARBALL" ]]; then
  echo "LLAMA_SOURCE_TARBALL $SOURCE_TARBALL"
  rm -rf "$SRC_DIR"
  mkdir -p "$SRC_DIR"
  tar -xzf "$SOURCE_TARBALL" -C "$SRC_DIR" --strip-components=1
  cd "$SRC_DIR"
elif [[ -d "$SRC_DIR/.git" ]]; then
  echo "LLAMA_SOURCE_EXISTING $SRC_DIR"
  cd "$SRC_DIR"
  git fetch origin pull/24423/head:diffusiongemma-pr24423
  git checkout diffusiongemma-pr24423
else
  echo "LLAMA_SOURCE_CLONE $SRC_DIR"
  git clone https://github.com/ggml-org/llama.cpp.git "$SRC_DIR"
  cd "$SRC_DIR"
  git fetch origin pull/24423/head:diffusiongemma-pr24423
  git checkout diffusiongemma-pr24423
fi

if [[ -d "$SRC_DIR/.git" ]]; then
  echo "LLAMA_COMMIT $(git rev-parse HEAD)"
else
  echo "LLAMA_COMMIT $(cat "$SOURCE_SHA_FILE" 2>/dev/null || echo unknown-tarball-source)"
fi
echo "LLAMA_STATUS"
if [[ -d "$SRC_DIR/.git" ]]; then
  git status --short
else
  echo "source extracted from tarball; no .git directory"
fi

cmake -S . -B build \
  -DGGML_CUDA=ON \
  -DGGML_CUDA_FA=ON \
  -DCMAKE_CUDA_COMPILER=/usr/local/cuda/bin/nvcc \
  -DCMAKE_CUDA_ARCHITECTURES=89 \
  -DCMAKE_BUILD_TYPE=Release

cmake --build build --config Release -j --target llama-diffusion-cli

echo "DIFFUSION_HELP"
build/bin/llama-diffusion-cli --help > "$LOG_DIR/llama-diffusion-cli-help.txt" 2>&1 || true
sed -n '1,220p' "$LOG_DIR/llama-diffusion-cli-help.txt"

echo "PREPARE_DONE $(date -Is)"
