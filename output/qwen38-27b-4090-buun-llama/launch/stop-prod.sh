#!/usr/bin/env bash
# Stop production so a trial llama-server can own the 4090.
set -euo pipefail
WRAP="${SUDO_WRAP:-/home/hhtele/qwen38-dflash2-20260819/launch/sudo-wrap.sh}"
if [[ -x "$WRAP" ]]; then
  "$WRAP" systemctl stop openclaw-qwen38-work-64k.service
else
  sudo systemctl stop openclaw-qwen38-work-64k.service
fi
pkill -f "llama-server.*18443" 2>/dev/null || true
sleep 2
nvidia-smi --query-gpu=memory.used,memory.free --format=csv,noheader
ss -ltn | grep -E '18343|18443' || true
