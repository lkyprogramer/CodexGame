#!/usr/bin/env bash
set -euo pipefail

RUN_DIR="/home/hhtele/diffusiongemma-26b-a4b-4bit-4090-20260612"
RESULT_DIR="$RUN_DIR/results"
LOG_DIR="$RUN_DIR/logs"
SERVICE="openclaw-qwen36-mtp4-128k.service"
TOKEN="${QWEN_NGINX_TOKEN:-}"

mkdir -p "$RESULT_DIR" "$LOG_DIR"

restore_service() {
  set +e
  pkill -f 'llama-diffusion-cli' || true
  pkill -f 'llama-server.*19343' || true
  printf 'hhtele\n' | sudo -S systemctl start "$SERVICE" >/dev/null 2>&1
  sleep 8
  {
    echo "RESTORE_STATUS $(date -Is)"
    systemctl is-active "$SERVICE"
    systemctl is-enabled "$SERVICE"
    echo "LOCAL_18343"
    curl -sS -m 30 http://127.0.0.1:18343/v1/models
    echo
    if [[ -n "$TOKEN" ]]; then
      echo "LOCAL_28343_AUTH"
      curl -sS -m 30 -H "Authorization: Bearer $TOKEN" http://127.0.0.1:28343/v1/models
      echo
    fi
    echo "LOCAL_28343_NOAUTH_STATUS"
    curl -sS -m 30 -o /tmp/diffusiongemma-noauth.out -w "%{http_code}" http://127.0.0.1:28343/v1/models
    echo
    cat /tmp/diffusiongemma-noauth.out 2>/dev/null || true
    echo
    echo "NO_DIFFUSION_RESIDUAL"
    ps -eo pid,ppid,stat,pcpu,pmem,args | grep -E 'llama-diffusion-cli|llama-server.*19343' | grep -v grep || true
    echo "GPU"
    nvidia-smi --query-gpu=name,driver_version,memory.total,memory.used,memory.free,utilization.gpu,power.draw,power.limit --format=csv,noheader
  } > "$LOG_DIR/restore-status.log" 2>&1
}

trap restore_service EXIT INT TERM

{
  echo "EVAL_START $(date -Is)"
  echo "SERVICE_BEFORE"
  systemctl is-active "$SERVICE" || true
  systemctl is-enabled "$SERVICE" || true
  echo "LOCAL_18343_BEFORE"
  curl -sS -m 30 http://127.0.0.1:18343/v1/models || true
  echo
  echo "GPU_BEFORE"
  nvidia-smi --query-gpu=name,driver_version,memory.total,memory.used,memory.free,utilization.gpu,power.draw,power.limit --format=csv,noheader
} > "$LOG_DIR/pre-eval-status.log" 2>&1

printf 'hhtele\n' | sudo -S systemctl stop "$SERVICE" >/dev/null
sleep 8
pkill -f 'llama-diffusion-cli' || true
pkill -f 'llama-server.*19343' || true
sleep 3

python3 "$RUN_DIR/diffusiongemma_4bit_eval.py" 2>&1 | tee "$RESULT_DIR/eval.log"
