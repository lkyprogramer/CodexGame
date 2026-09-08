#!/usr/bin/env bash
set -euo pipefail
WRAP=/home/hhtele/qwen38-dflash2-20260819/launch/sudo-wrap.sh
docker rm -f ninfer-4090 ninfer-4090-prod >/dev/null 2>&1 || true
if systemctl list-unit-files openclaw-qwen38-ninfer.service >/dev/null 2>&1; then
  "$WRAP" systemctl start openclaw-qwen38-ninfer.service || true
else
  "$WRAP" systemctl start openclaw-qwen38-work-64k.service || true
fi
for i in $(seq 1 120); do
  curl -fsS --max-time 3 http://127.0.0.1:18343/v1/models >/dev/null 2>&1 && { echo prod_ready ${i}s; exit 0; }
  sleep 2
done
echo prod_restore_failed
exit 1
