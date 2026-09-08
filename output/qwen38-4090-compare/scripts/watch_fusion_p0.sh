#!/usr/bin/env bash
# Silent until P0 terminal. Extra diagnostics go to watch log.
set -u
PID="${1:?}"
ST="/Users/luo/Documents/github/CodexGame/output/qwen38-4090-compare/logs/fusion.status"
LOG="/Users/luo/Documents/github/CodexGame/output/qwen38-4090-compare/logs/fusion-p0.out"
WLOG="/Users/luo/Documents/github/CodexGame/output/qwen38-4090-compare/logs/watch-fusion-p0.$PID.log"
while :; do
  if grep -q 'FUSION_P0_OK' "$ST" 2>/dev/null; then
    echo "DONE: FUSION_P0_OK"
    exit 0
  fi
  if grep -q 'FUSION_P0_FAIL' "$ST" 2>/dev/null; then
    echo "FAILED: FUSION_P0_FAIL"
    exit 1
  fi
  if ! kill -0 "$PID" 2>/dev/null; then
    echo "FAILED: runner pid $PID exited without P0 terminal"
    exit 1
  fi
  date -Iseconds >>"$WLOG"
  tail -n 3 "$ST" >>"$WLOG" 2>/dev/null || true
  sleep 30
done
