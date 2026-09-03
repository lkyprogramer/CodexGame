#!/usr/bin/env bash
set -euo pipefail
pkill -f "llama-server.*18443" 2>/dev/null || true
sleep 2
WRAP="${SUDO_WRAP:-/home/hhtele/qwen38-dflash2-20260819/launch/sudo-wrap.sh}"
if [[ -x "$WRAP" ]]; then
  "$WRAP" systemctl start openclaw-qwen38-work-64k.service
else
  sudo systemctl start openclaw-qwen38-work-64k.service
fi
for i in $(seq 1 90); do
  if curl -fsS http://127.0.0.1:18343/v1/models >/dev/null 2>&1; then
    echo "prod_ready after ${i}s"
    curl -fsS http://127.0.0.1:18343/v1/models
    nvidia-smi --query-gpu=memory.used,memory.free --format=csv,noheader
    exit 0
  fi
  sleep 2
done
echo "prod_restore_failed" >&2
exit 1
