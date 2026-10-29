#!/usr/bin/env bash
set -euo pipefail
export PYTHONPATH=/work
export OMP_NUM_THREADS=8 OPENBLAS_NUM_THREADS=8 MKL_NUM_THREADS=8
policy=$(/work/releases/ovis/bin/python -c 'import json; print(json.dumps(json.load(open("/work/evidence/ovis-effective-runtime.json"))["policy"]))')
exec /work/releases/ovis/bin/python -m ocrbench.cli \
    --adapter ovis --manifest /work/corpus/manifest.json \
    --out /work/results/ovis-full-r1 --base-url http://127.0.0.1:18500/v1 \
    --model ovisocr3 --model-dir /models/OvisOCR3 \
    --option profile='"C0-S0-full-diagnostic"' --option "runtime_policy=$policy" \
    --option build_interference=true \
    --option model_process_lifecycle='"existing standard process after development checks"'
