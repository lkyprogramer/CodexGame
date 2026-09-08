#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
source "$ROOT/scripts/common.sh"; load_bench_env
base=${SERVER_URL%/v1}
limit=${WAIT_SERVER_SEC:-900}
start=$(date +%s)
while true; do
  if curl -fsS -H "Authorization: Bearer $API_KEY" "$base/health" >/dev/null 2>&1 || \
     curl -fsS -H "Authorization: Bearer $API_KEY" "$SERVER_URL/models" >/dev/null 2>&1; then
    log 'server ready'; exit 0
  fi
  now=$(date +%s); (( now-start < limit )) || { echo "server not ready after ${limit}s"; exit 1; }
  sleep 5
  echo "[$(ts)] waiting for server..."
done
