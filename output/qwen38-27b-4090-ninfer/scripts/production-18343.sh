#!/usr/bin/env bash
# Production NInfer on 18343 via compat proxy. Model id matches WORK.
# Engine listens on 127.0.0.1:18030. Proxy is the systemd main process.
set -euo pipefail
MODEL=/data/models/qwen/qwen38-ninfer/qwen3_8_27b.ninfer
IMAGE=ninfer-4090:44a2c6c
NAME=ninfer-4090-prod
PROXY=/home/hhtele/ninfer-4090/launch/openai_compat_proxy.py

mkdir -p /home/hhtele/ninfer-4090/cache /home/hhtele/ninfer-4090/logs /var/log/llama

docker rm -f "$NAME" ninfer-4090 >/dev/null 2>&1 || true

docker run -d --name "$NAME" --gpus all --restart=no --network host \
  -v "$MODEL:/opt/ninfer/models/qwen3_8_27b.ninfer:ro" \
  -v /home/hhtele/ninfer-4090/cache:/var/cache/ninfer \
  "$IMAGE" \
  /opt/ninfer/models/qwen3_8_27b.ninfer \
  --model-id openclaw/Qwen3.8-27B-WORK \
  --host 127.0.0.1 --port 18030 \
  --max-context 262144 --kv-capacity 262144 \
  --max-concurrency 1 --max-pending-requests 8 \
  --pending-timeout-ms 600000 \
  --prefill-chunk 1024 --kv-dtype rk4v4-e8 \
  --spec mtp --draft-tokens 3 --lm-head-draft \
  --prefix-checkpoint-policy rolling-tool \
  --continuation-cache l1-l2 \
  --continuation-cache-l1-mib 6144 \
  --continuation-cache-l2-mib 8192 \
  --preserve-thinking \
  --default-max-tokens 32768 \
  --temperature 1.0 --top-p 0.95 --top-k 20 --presence-penalty 0.0

for i in $(seq 1 180); do
  if curl -fsS --max-time 2 http://127.0.0.1:18030/v1/models >/dev/null 2>&1; then
    echo "NINFER_ENGINE_READY ${i}s"
    exec python3 "$PROXY"
  fi
  docker ps -a --filter name="$NAME" --format '{{.Status}}' | grep -q Exited && {
    echo NINFER_ENGINE_DIED
    docker logs "$NAME" 2>&1 | tail -n 80
    exit 1
  }
  sleep 2
done
echo NINFER_ENGINE_NOT_READY
exit 1
