#!/usr/bin/env bash
set -euo pipefail
export PYTHONPATH=/work OMP_NUM_THREADS=8 OPENBLAS_NUM_THREADS=8 MKL_NUM_THREADS=8
/work/releases/ovis/bin/python - <<'PY'
import time, urllib.request
deadline = time.monotonic() + 900
while time.monotonic() < deadline:
    try:
        with urllib.request.urlopen('http://127.0.0.1:18500/v1/models', timeout=3) as response:
            if response.status == 200:
                break
    except OSError:
        pass
    time.sleep(1)
else:
    raise SystemExit('O1 readiness deadline exceeded')
PY
/work/releases/ovis/bin/python - <<'PY'
from pathlib import Path
import json, os
argv = Path('/proc/1/cmdline').read_bytes().decode().strip('\0').split('\0')
Path('/work/evidence/' + os.environ.get('OCR_O1_TAG', 'ovis-o1-16k-r1') + '-policy.json').write_text(
    json.dumps({'pid1_argv': argv, 'scope': 'live container PID1 after API readiness'}, indent=2))
PY
exec /work/releases/ovis/bin/python -m ocrbench.extra_cli \
    --stage1-run "${OCR_O1_STAGE1:-/work/results/ovis-full-c0-v3}" --pairs "${OCR_O1_PAIRS:-/work/evidence/ovis-o1-pairs.json}" \
    --out "/work/results/${OCR_O1_TAG:-ovis-o1-16k-r1}" --base-url http://127.0.0.1:18500/v1 \
    --profile "${OCR_O1_PROFILE:-O1-16K-PRED}" \
    --service-policy-evidence "/work/evidence/${OCR_O1_TAG:-ovis-o1-16k-r1}-policy.json" \
    --model ovisocr3 --model-dir /models/OvisOCR3
