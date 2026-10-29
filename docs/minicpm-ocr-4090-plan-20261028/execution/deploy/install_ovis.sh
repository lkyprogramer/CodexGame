#!/usr/bin/env bash
set -euo pipefail
export PATH=/work/releases/tools/bin:$PATH
export UV_CACHE_DIR=/work/cache/uv UV_PYTHON_INSTALL_DIR=/work/releases/python
export UV_PYTHON_PREFERENCE=only-system
uv venv --python 3.12 /work/releases/ovis
uv pip install --python /work/releases/ovis/bin/python 'vllm==0.22.1' pillow 'pymupdf==1.26.7' requests pytest 'apted==1.0.3' 'lxml==5.4.0'
uv pip check --python /work/releases/ovis/bin/python
uv pip freeze --python /work/releases/ovis/bin/python > /work/evidence/ovis-freeze.txt
/work/releases/ovis/bin/python -c 'import torch,transformers,vllm; print(torch.__version__,torch.version.cuda,transformers.__version__,vllm.__version__)'
/work/releases/ovis/bin/vllm serve --help > /work/evidence/ovis-serve-help.txt
date -u +%FT%TZ > /work/evidence/ovis-install-complete.txt
