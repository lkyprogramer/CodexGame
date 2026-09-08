#!/usr/bin/env bash
# Run ON 4090. build | prepare | start | stop-restore
set -euo pipefail
WRAP=/home/hhtele/qwen38-dflash2-20260819/launch/sudo-wrap.sh
UP=/home/hhtele/qwen38-vllm
LOG=/home/hhtele/qwen38-vllm/logs
CMD="${1:?build|prepare|start|stop-restore}"
mkdir -p "$LOG"

case "$CMD" in
  build)
    docker tag docker.m.daocloud.io/nvidia/cuda:13.0.1-base-ubuntu24.04 nvidia/cuda:13.0.1-base-ubuntu24.04 2>/dev/null || true
    cd "$UP"
    docker compose build 2>&1 | tee "$LOG/docker-build.log"
    echo VLLM_BUILD_OK
    ;;
  prepare)
    cd "$UP"
    export HF_ENDPOINT=https://hf-mirror.com
    export HF_HUB_DISABLE_XET=1
    export HF_HUB_ENABLE_HF_TRANSFER=1
    docker compose run --rm \
      -e HF_ENDPOINT=https://hf-mirror.com \
      -e HF_HUB_DISABLE_XET=1 \
      -e HF_HUB_ENABLE_HF_TRANSFER=1 \
      prepare 2>&1 | tee "$LOG/prepare.log"
    echo VLLM_PREPARE_OK
    ;;
  start)
    "$WRAP" systemctl stop openclaw-qwen38-ninfer.service || true
    "$WRAP" systemctl stop openclaw-qwen38-work-64k.service || true
    sleep 3
    cd "$UP"
    docker compose --profile single down --remove-orphans >/dev/null 2>&1 || true
    docker compose --profile single up -d
    echo VLLM_START_ISSUED
    ;;
  stop-restore)
    cd "$UP"
    docker compose --profile single down --remove-orphans >/dev/null 2>&1 || true
    if systemctl list-unit-files openclaw-qwen38-ninfer.service >/dev/null 2>&1; then
      "$WRAP" systemctl start openclaw-qwen38-ninfer.service || true
    else
      "$WRAP" systemctl start openclaw-qwen38-work-64k.service || true
    fi
    for i in $(seq 1 90); do
      curl -fsS --max-time 3 http://127.0.0.1:18343/v1/models >/dev/null 2>&1 && { echo prod_ready ${i}s; exit 0; }
      sleep 2
    done
    echo prod_restore_failed
    exit 1
    ;;
esac
