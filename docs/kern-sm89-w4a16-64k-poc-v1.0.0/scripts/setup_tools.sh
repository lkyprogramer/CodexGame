#!/usr/bin/env bash
# Optional isolated CPU-tool dependencies; no GPU/service/driver mutations.
set -euo pipefail
cd "$(dirname "$0")/.."
PYTHON="${PYTHON:-python3}"
if [[ ! -x .venv/bin/python ]]; then "$PYTHON" -m venv .venv; fi
if [[ -n "${WHEELHOUSE:-}" ]]; then
  .venv/bin/python -m pip install --no-index --find-links "$WHEELHOUSE" -r configs/requirements-tools.txt
elif [[ "${ALLOW_NETWORK:-0}" == 1 ]]; then
  .venv/bin/python -m pip install -r configs/requirements-tools.txt
else
  echo 'BLOCKED: set WHEELHOUSE=/path/to/offline/wheels or explicitly ALLOW_NETWORK=1. No global packages were changed.' >&2
  exit 78
fi
mkdir -p work
.venv/bin/python -m pip freeze > work/tools-pip-freeze.txt
printf '%s\n' 'Tools ready. Run: source .venv/bin/activate && bash scripts/self_check.sh'
