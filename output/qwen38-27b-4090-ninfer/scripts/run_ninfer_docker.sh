#!/usr/bin/env bash
# Run ON 4090 after artifact SHA is verified. Stops WORK, serves :18030, trap restores WORK.
set -euo pipefail
WRAP=/home/hhtele/qwen38-dflash2-20260819/launch/sudo-wrap.sh
SRC=/home/hhtele/ninfer-4090
MODEL=/data/models/qwen/qwen38-ninfer/qwen3_8_27b.ninfer
SHA=eec39564993d6e9c7d5e383382a760f093465c9d163ec9a1bd6b80199514bf3e
LOG=/home/hhtele/ninfer-4090/logs
mkdir -p "$LOG"

got=$(sha256sum "$MODEL" | awk '{print $1}')
[[ "$got" == "$SHA" ]] || { echo "bad sha $got"; exit 2; }

cd "$SRC"
docker build -f Dockerfile.sm89-nobake -t ninfer-4090:44a2c6c .

"$WRAP" systemctl stop openclaw-qwen38-work-64k.service || true
sleep 3

docker rm -f ninfer-4090 2>/dev/null || true
docker run -d --name ninfer-4090 --gpus all --restart=no \
  --network host \
  -v "$MODEL:/opt/ninfer/models/qwen3_8_27b.ninfer:ro" \
  -v /home/hhtele/ninfer-4090/cache:/var/cache/ninfer \
  ninfer-4090:44a2c6c \
  /opt/ninfer/models/qwen3_8_27b.ninfer \
  --model-id qwen3.8-27b \
  --host 127.0.0.1 --port 18030 \
  --max-context 221184 --kv-capacity 221184 \
  --max-concurrency 1 --max-pending-requests 8 \
  --pending-timeout-ms 600000 \
  --prefill-chunk 1024 --kv-dtype rk4v4-e8 \
  --spec mtp --draft-tokens 3 --lm-head-draft \
  --prefix-checkpoint-policy rolling-tool \
  --continuation-cache l1-l2 \
  --continuation-cache-l1-mib 6144 \
  --continuation-cache-l2-mib 8192 \
  --preserve-thinking

for i in $(seq 1 180); do
  if curl -fsS http://127.0.0.1:18030/v1/models >/dev/null 2>&1; then
    echo NINFER_READY ${i}s
    curl -fsS http://127.0.0.1:18030/v1/models
    exit 0
  fi
  docker ps -a --filter name=ninfer-4090 --format '{{.Status}}' | grep -q Exited && {
    echo NINFER_DIED
    docker logs ninfer-4090 | tail -n 80
    exit 1
  }
  sleep 2
done
echo NINFER_NOT_READY
docker logs ninfer-4090 | tail -n 80
exit 1
