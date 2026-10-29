#!/usr/bin/env bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
# CUDA is supplied by the base image and locked Python environment. NVIDIA's
# optional apt mirror had inconsistent index sizes during this run.
if test -f /etc/apt/sources.list.d/cuda-ubuntu2404-x86_64.list; then
    mv /etc/apt/sources.list.d/cuda-ubuntu2404-x86_64.list /etc/apt/sources.list.d/cuda-ubuntu2404-x86_64.list.disabled
fi
apt-get update
apt-get install -y ca-certificates curl git build-essential gcc-13 g++-13 libdw-dev libelf-dev pkg-config libgl1 libglib2.0-0 python3 python3-venv python3-pip unzip fonts-noto-cjk fonts-liberation
python3 -m venv /work/releases/tools
/work/releases/tools/bin/pip install uv==0.10.10
export PATH=/work/releases/tools/bin:$PATH
export UV_CACHE_DIR=/work/cache/uv UV_PYTHON_INSTALL_DIR=/work/releases/python
export UV_PYTHON_PREFERENCE=only-system
# Ubuntu's installed CPython 3.12 satisfies the plan. Avoid an additional
# GitHub-hosted interpreter download; record its exact patch below.
python3.12 --version
gcc-13 --version
uv --version
nvidia-smi --query-gpu=name,driver_version,memory.total,memory.used --format=csv
date -u +%FT%TZ > /work/evidence/bootstrap-complete.txt
