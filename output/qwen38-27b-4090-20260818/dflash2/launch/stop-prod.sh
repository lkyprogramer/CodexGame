#!/usr/bin/env bash
# Stop production so a trial llama-server can own the 4090.
set -euo pipefail
sudo systemctl stop openclaw-qwen38-work-64k.service
pkill -f "llama-server.*18443" 2>/dev/null || true
sleep 2
nvidia-smi --query-gpu=memory.used,memory.free --format=csv,noheader
ss -ltnp | grep -E '18343|18443' || true
