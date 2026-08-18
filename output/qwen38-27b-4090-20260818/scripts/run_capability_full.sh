#!/usr/bin/env bash
set -u
ROOT=/home/hhtele/qwen38-27b-4090-20260818
PY="$ROOT/capability/.venv/bin/python"
# fallback
if [ ! -x "$PY" ]; then PY=python3; fi
export PYTHONUNBUFFERED=1
export QWEN38_BASE=http://127.0.0.1:18343
export QWEN38_MODEL=openclaw/Qwen3.8-27B-WORK
export CAP_ROOT=$ROOT/capability
LOG=$ROOT/capability/full.log
{
  echo START=$(date -Is)
  for s in t4 t6 t1 t8 t5 t2 t3 t7 t9; do
    echo "===== $s $(date -Is) ====="
    "$PY" "$ROOT/scripts/capability_eval.py" --suite "$s"
    echo "===== $s rc=$? $(date -Is) ====="
  done
  echo DONE=$(date -Is)
} >>"$LOG" 2>&1
