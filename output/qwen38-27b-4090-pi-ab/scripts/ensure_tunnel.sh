#!/usr/bin/env bash
# Keep a local 18343 tunnel to 4090. Idempotent.
set -euo pipefail
if curl -fsS --max-time 2 http://127.0.0.1:18343/v1/models >/dev/null 2>&1; then
  echo "tunnel already up"
  exit 0
fi
pkill -f "ssh .*18343:127.0.0.1:18343" 2>/dev/null || true
ssh -f -N -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 \
  -L 127.0.0.1:18343:127.0.0.1:18343 hhtele@192.168.10.29
sleep 1
curl -fsS --max-time 5 http://127.0.0.1:18343/v1/models >/dev/null
echo "tunnel ready"
