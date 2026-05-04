#!/usr/bin/env bash
set -euo pipefail

mkdir -p /data/models/qwen/.downloads/qwen36-dflash
pid=/data/models/qwen/.downloads/qwen36-dflash/remote_parts_download.pid
log=/data/models/qwen/.downloads/qwen36-dflash/remote_parts_download.log

if [ -f "$pid" ] && kill -0 "$(cat "$pid")" 2>/dev/null; then
  echo "download job already running: $(cat "$pid")"
else
  rm -f \
    /data/models/qwen/.downloads/qwen36-dflash/remote_parts_download_progress.jsonl \
    /data/models/qwen/.downloads/qwen36-dflash/remote_parts_download_state.json \
    "$log"
  nohup python3 /tmp/qwen36_remote_parts_download.py > "$log" 2>&1 &
  echo $! > "$pid"
  echo "download job started: $(cat "$pid")"
fi

printf "### pid\n"
cat "$pid"
printf "### log\n"
tail -n 20 "$log" 2>/dev/null || true
