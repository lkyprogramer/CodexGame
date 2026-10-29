#!/usr/bin/env bash
set -euo pipefail
export PATH=/work/releases/tools/bin:$PATH
export UV_CACHE_DIR=/work/cache/uv UV_PYTHON_PREFERENCE=only-system
export CC=gcc-13 CXX=g++-13 CUDAHOSTCXX=g++-13 MAX_JOBS=4 NVCC_THREADS=1 TORCH_CUDA_ARCH_LIST=8.9
cd /opt/minicpm-ocr
export CUDA_HOME=$(.venv-vllm/bin/python -c 'import sysconfig; print(sysconfig.get_path("purelib") + "/nvidia/cu13")')
export PATH="$CUDA_HOME/bin:$PATH" FLASHINFER_NVCC="$CUDA_HOME/bin/nvcc"
source /work/releases/cmake-archives/cmake-dependency-env.sh /work/releases/cmake-src
"$CUDA_HOME/bin/nvcc" --version
uv pip install --python .venv-vllm/bin/python -r pyproject.toml --extra vllm-build --extra vllm --no-build-isolation-package vllm
uv pip check --python .venv-vllm/bin/python
uv pip freeze --python .venv-vllm/bin/python > /work/evidence/mini-vllm-freeze.txt
uv pip freeze --python .venv-sdk-cpu/bin/python > /work/evidence/mini-sdk-freeze.txt
.venv-vllm/bin/python -c 'import torch,transformers,vllm; print(torch.__version__,torch.version.cuda,transformers.__version__,vllm.__version__)'
.venv-vllm/bin/vllm serve --help=all > /work/evidence/mini-serve-help-all.txt
git -C sources/vllm diff > /work/evidence/mini-vllm-install.patch
date -u +%FT%TZ > /work/evidence/mini-install-complete.txt
