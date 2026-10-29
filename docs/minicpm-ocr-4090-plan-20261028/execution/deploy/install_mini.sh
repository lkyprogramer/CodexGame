#!/usr/bin/env bash
set -euo pipefail
export PATH=/work/releases/tools/bin:$PATH
export UV_CACHE_DIR=/work/cache/uv UV_PYTHON_INSTALL_DIR=/work/releases/python
export UV_PYTHON_PREFERENCE=only-system
cd /opt/minicpm-ocr
git init
git remote add origin https://github.com/OpenBMB/MiniCPM-OCR.git
git fetch --depth 1 origin 62d5e649c32be2271f2c8c66ec8307f3d7373903
git checkout --detach FETCH_HEAD
mkdir -p sources
for entry in 'vllm https://github.com/vllm-project/vllm.git 18343393b4da41a7e8027efbc4c7e77c28301bf0' 'transformers https://github.com/huggingface/transformers.git 549e5b410733fb50e8efbbe4aa585cb89f6478ea'; do
    read -r name repository revision <<< "$entry"
    git init "sources/$name"
    git -C "sources/$name" remote add origin "$repository"
    git -C "sources/$name" fetch --depth 1 origin "$revision"
    git -C "sources/$name" checkout --detach FETCH_HEAD
done
export OCR_PYTHON=3.12 CC=gcc-13 CXX=g++-13 CUDAHOSTCXX=g++-13
export MAX_JOBS=4 NVCC_THREADS=1 TORCH_CUDA_ARCH_LIST=8.9
bash scripts/install.sh sdk-cpu
uv pip install --python .venv-sdk-cpu/bin/python 'pymupdf==1.26.7' requests pytest 'apted==1.0.3' 'lxml==5.4.0'
bash scripts/install.sh vllm
uv pip freeze --python .venv-vllm/bin/python > /work/evidence/mini-vllm-freeze.txt
uv pip freeze --python .venv-sdk-cpu/bin/python > /work/evidence/mini-sdk-freeze.txt
.venv-vllm/bin/python -c 'import torch,transformers,vllm; print(torch.__version__,torch.version.cuda,transformers.__version__,vllm.__version__)'
.venv-vllm/bin/vllm serve --help > /work/evidence/mini-serve-help.txt
git -C sources/vllm diff > /work/evidence/mini-vllm-install.patch
date -u +%FT%TZ > /work/evidence/mini-install-complete.txt
