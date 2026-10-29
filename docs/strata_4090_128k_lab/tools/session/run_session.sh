#!/bin/sh
# usage: run_session.sh NAME [session_bench args...]
# LAB_PYTHON defaults to the Python used on 29 (the deployed Strata venv).
set -e
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
PY=${LAB_PYTHON:-/home/hhtele/strata-0.1.43.1/.venv/bin/python}
export PATH="$(dirname "$PY"):$PATH"
N=$1; shift
mkdir -p "$ROOT/workspace/reports/session"
cd "$ROOT"
exec "$PY" tools/session/session_bench.py --name "$N" "$@" > "workspace/reports/session/$N.log" 2>&1
