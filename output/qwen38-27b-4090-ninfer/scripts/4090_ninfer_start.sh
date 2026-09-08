#!/usr/bin/env bash
# Start existing ninfer-4090:44a2c6c on :18030. Stops WORK. No rebuild.
set -euo pipefail
WRAP=/home/hhtele/qwen38-dflash2-20260819/launch/sudo-wrap.sh
MODEL=/data/models/qwen/qwen38-ninfer/qwen3_8_27b.ninfer
DRAFT="${DRAFT_TOKENS:-3}"
CTX="${NINFER_CTX:-221184}"
KVDTYPE="${NINFER_KV:-rk4v4-e8}"
L1="${NINFER_L1_MIB:-6144}"
L2="${NINFER_L2_MIB:-8192}"
L3="${NINFER_L3_MIB:-16384}"
CACHE="${NINFER_CACHE:-l1-l2}"
CACHE_EXTRA=()
if [[ "$CACHE" == *l3* ]]; then
  CACHE_EXTRA+=(--continuation-cache-dir /var/cache/ninfer --continuation-cache-namespace local --continuation-cache-l3-mib "$L3")
fi
# Recreate unless NINFER_KEEP=1. Skipping restart would reuse old --draft-tokens.
if docker ps --format '{{.Names}}' | grep -qx ninfer-4090; then
  if [[ "${NINFER_KEEP:-0}" == 1 ]] && curl -fsS --max-time 3 http://127.0.0.1:18030/v1/models >/dev/null; then
    echo NINFER_ALREADY
    exit 0
  fi
  docker rm -f ninfer-4090 >/dev/null || true
fi
"$WRAP" systemctl stop openclaw-qwen38-ninfer.service || true
"$WRAP" systemctl stop openclaw-qwen38-work-64k.service || true
sleep 3
docker rm -f ninfer-4090 >/dev/null 2>&1 || true
mkdir -p /home/hhtele/ninfer-4090/cache /home/hhtele/ninfer-4090/logs
docker run -d --name ninfer-4090 --gpus all --restart=no --network host \
  -v "$MODEL:/opt/ninfer/models/qwen3_8_27b.ninfer:ro" \
  -v /home/hhtele/ninfer-4090/cache:/var/cache/ninfer \
  ninfer-4090:44a2c6c \
  /opt/ninfer/models/qwen3_8_27b.ninfer \
  --model-id qwen3.8-27b \
  --host 127.0.0.1 --port 18030 \
  --max-context "$CTX" --kv-capacity "$CTX" \
  --max-concurrency 1 --max-pending-requests 8 \
  --pending-timeout-ms 600000 \
  --prefill-chunk 1024 --kv-dtype "$KVDTYPE" \
  --spec mtp --draft-tokens "$DRAFT" --lm-head-draft \
  --prefix-checkpoint-policy rolling-tool \
  --continuation-cache "$CACHE" \
  --continuation-cache-l1-mib "$L1" \
  --continuation-cache-l2-mib "$L2" \
  "${CACHE_EXTRA[@]}" \
  --preserve-thinking
for i in $(seq 1 180); do
  if curl -fsS --max-time 2 http://127.0.0.1:18030/v1/models >/dev/null 2>&1; then
    echo NINFER_READY ${i}s ctx=$CTX kv=$KVDTYPE draft=$DRAFT l1=$L1 cache=$CACHE
    nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader || true
    docker inspect ninfer-4090 --format '{{json .Args}}' || true
    exit 0
  fi
  docker ps -a --filter name=ninfer-4090 --format '{{.Status}}' | grep -q Exited && {
    echo NINFER_DIED
    docker logs ninfer-4090 2>&1 | tail -n 80
    exit 1
  }
  sleep 2
done
echo NINFER_NOT_READY
exit 1
