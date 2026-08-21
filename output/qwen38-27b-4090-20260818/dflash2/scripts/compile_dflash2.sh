#!/usr/bin/env bash
# Unpack the locally-relayed llama.cpp PR tree and build llama-server for sm_89.
set -euo pipefail
TAR="${1:-/home/hhtele/llama.cpp-qwen38-dflash2-pr27342.tar.gz}"
DEST="${2:-/home/hhtele/llama.cpp-qwen38-dflash2-pr27342}"
export PATH=/usr/local/cuda/bin:$PATH
export LD_LIBRARY_PATH=/usr/local/cuda/lib64:${LD_LIBRARY_PATH:-}
rm -rf "$DEST"
mkdir -p "$(dirname "$DEST")"
tar -xzf "$TAR" -C "$(dirname "$DEST")"
cd "$DEST"
cmake -B build -DCMAKE_BUILD_TYPE=Release -DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=89
cmake --build build --target llama-server -j"$(nproc)"
./build/bin/llama-server --version | head -20 || true
ls -lh ./build/bin/llama-server
