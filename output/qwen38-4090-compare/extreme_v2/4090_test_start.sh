#!/usr/bin/env bash
# Exclusive test container. Does not enable a new systemd default.
set -euo pipefail
WRAP=/home/hhtele/qwen38-dflash2-20260819/launch/sudo-wrap.sh
MODEL=/data/models/qwen/qwen38-ninfer/qwen3_8_27b.ninfer
IMAGE=ninfer-4090:44a2c6c
NAME=ninfer-4090
DRAFT="${DRAFT_TOKENS:-3}"
CTX="${NINFER_CTX:-200192}"
KVDTYPE="${NINFER_KV:-rk4v4-e8}"
SPEC="${NINFER_SPEC:-mtp}"
L1="${NINFER_L1_MIB:-6144}"
L2="${NINFER_L2_MIB:-8192}"
REQLOG="${NINFER_REQUEST_LOG:-/var/log/ninfer/ninfer-request.jsonl}"
LMHEAD="${NINFER_LMHEAD:-1}"

$WRAP systemctl stop openclaw-qwen38-ninfer.service || true
docker rm -f "$NAME" ninfer-4090-prod >/dev/null 2>&1 || true
mkdir -p /home/hhtele/ninfer-4090/cache /home/hhtele/ninfer-4090/logs
: > /home/hhtele/ninfer-4090/logs/ninfer-request.jsonl

EXTRA=()
if [[ "$SPEC" != "off" ]]; then
  EXTRA+=(--spec "$SPEC" --draft-tokens "$DRAFT")
  if [[ "$LMHEAD" == "1" && "$SPEC" == "mtp" ]]; then
    EXTRA+=(--lm-head-draft)
  fi
fi

docker run -d --name "$NAME" --gpus all --restart=no --network host \
  -v "$MODEL:/opt/ninfer/models/qwen3_8_27b.ninfer:ro" \
  -v /home/hhtele/ninfer-4090/cache:/var/cache/ninfer \
  -v /home/hhtele/ninfer-4090/logs:/var/log/ninfer \
  "$IMAGE" \
  /opt/ninfer/models/qwen3_8_27b.ninfer \
  --model-id qwen3.8-27b \
  --host 127.0.0.1 --port 18030 \
  --max-context "$CTX" --kv-capacity "$CTX" \
  --max-concurrency 1 --max-pending-requests 8 \
  --pending-timeout-ms 600000 \
  --prefill-chunk 1024 --kv-dtype "$KVDTYPE" \
  --prefix-checkpoint-policy rolling-tool \
  --continuation-cache l1-l2 \
  --continuation-cache-l1-mib "$L1" \
  --continuation-cache-l2-mib "$L2" \
  --request-log-jsonl "$REQLOG" \
  --preserve-thinking \
  --default-max-tokens 32768 \
  --temperature 1.0 --top-p 0.95 --top-k 20 --presence-penalty 0.0 \
  "${EXTRA[@]}"

for i in $(seq 1 180); do
  if curl -fsS --max-time 2 http://127.0.0.1:18030/v1/models >/dev/null 2>&1; then
    echo "NINFER_READY ${i}s ctx=$CTX kv=$KVDTYPE spec=$SPEC draft=$DRAFT"
    nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader || true
    docker inspect "$NAME" --format '{{json .Args}}' || true
    exit 0
  fi
  docker ps -a --filter name="$NAME" --format '{{.Status}}' | grep -q Exited && {
    echo NINFER_DIED
    docker logs "$NAME" 2>&1 | tail -n 80
    exit 1
  }
  sleep 2
done
echo NINFER_NOT_READY
exit 1
