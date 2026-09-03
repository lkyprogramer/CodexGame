#!/usr/bin/env bash
# Unpack locally-relayed buun-llama-cpp and build llama-server for sm_89.
set -euo pipefail
TAR="${1:-/home/hhtele/buun-llama-cpp-87b37ea.tar.gz}"
DEST="${2:-/home/hhtele/buun-llama-cpp-87b37ea}"
export PATH=/usr/local/cuda/bin:$PATH
export LD_LIBRARY_PATH=/usr/local/cuda/lib64:${LD_LIBRARY_PATH:-}
mkdir -p "$(dirname "$DEST")"
if [[ ! -d "$DEST/.git" && ! -f "$DEST/CMakeLists.txt" ]]; then
  tar -xzf "$TAR" -C "$(dirname "$DEST")"
fi
cd "$DEST"
cmake -B build \
  -DCMAKE_BUILD_TYPE=Release \
  -DGGML_CUDA=ON \
  -DGGML_NATIVE=ON \
  -DGGML_CUDA_FA=ON \
  -DCMAKE_CUDA_ARCHITECTURES=89 \
  -DCMAKE_CUDA_COMPILER=/usr/local/cuda/bin/nvcc
cmake --build build --target llama-server -j"$(nproc)"
./build/bin/llama-server --version | head -20 || true
ls -lh ./build/bin/llama-server
