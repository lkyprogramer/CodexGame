#!/usr/bin/env bash
set -u
PID="${1:?}"
ST="/Users/luo/Documents/github/CodexGame/output/qwen38-4090-compare/logs/rewrite.status"
WLOG="/Users/luo/Documents/github/CodexGame/output/qwen38-4090-compare/logs/watch-rewrite.$PID.log"
while :; do
  if grep -q 'REWRITE_SUITE_OK' "$ST" 2>/dev/null; then
    echo "DONE: REWRITE_SUITE_OK"
    exit 0
  fi
  if grep -q 'REWRITE_SUITE_FAIL' "$ST" 2>/dev/null; then
    echo "FAILED: REWRITE_SUITE_FAIL"
    exit 1
  fi
  if ! kill -0 "$PID" 2>/dev/null; then
    echo "FAILED: runner pid $PID exited without SUITE terminal"
    exit 1
  fi
  date -Iseconds >>"$WLOG"
  tail -n 4 "$ST" >>"$WLOG" 2>/dev/null || true
  sleep 30
done
