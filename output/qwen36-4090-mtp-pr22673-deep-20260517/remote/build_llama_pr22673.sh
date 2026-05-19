#!/usr/bin/env bash
set -euo pipefail

DIR=/home/hhtele/llama.cpp-master-pr22673-20260517
LOG_DIR=/home/hhtele/qwen36-mtp-pr22673-deep-20260517/logs
mkdir -p "$LOG_DIR"

export PATH=/usr/local/cuda/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export LD_LIBRARY_PATH=/usr/local/cuda/lib64:${LD_LIBRARY_PATH:-}
export CUDACXX=/usr/local/cuda/bin/nvcc

if [ ! -d "$DIR/.git" ]; then
  git clone --depth 1 https://github.com/ggml-org/llama.cpp.git "$DIR"
else
  git -C "$DIR" fetch --depth 1 origin master
  git -C "$DIR" checkout -f origin/master
fi

echo "COMMIT $(git -C "$DIR" rev-parse --short HEAD)"

cmake -S "$DIR" -B "$DIR/build" \
  -DBUILD_SHARED_LIBS=OFF \
  -DLLAMA_BUILD_UI=OFF \
  -DLLAMA_BUILD_WEBUI=OFF \
  -DGGML_CUDA=ON \
  -DGGML_CUDA_FA=ON \
  -DGGML_CUDA_GRAPHS=ON \
  -DCMAKE_CUDA_COMPILER=/usr/local/cuda/bin/nvcc \
  -DCMAKE_CUDA_ARCHITECTURES=89 \
  -DCMAKE_BUILD_TYPE=Release

cmake --build "$DIR/build" --config Release -j 8 --target llama-server

"$DIR/build/bin/llama-server" --version 2>&1 | tee "$LOG_DIR/llama-server-version.txt"
"$DIR/build/bin/llama-server" --help 2>&1 \
  | grep -E -- 'draft-mtp|spec-draft-p-min|ngram-mod|spec-type|no-mmproj|cache-type-k|cache-type-v|ctx-checkpoints|cache-ram' \
  | tee "$LOG_DIR/llama-server-help-filtered.txt"
