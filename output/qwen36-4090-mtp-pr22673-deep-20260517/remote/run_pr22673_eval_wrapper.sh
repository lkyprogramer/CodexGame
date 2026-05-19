#!/usr/bin/env bash
set -euo pipefail

ROOT=/home/hhtele/qwen36-mtp-pr22673-deep-20260517
SERVICE=openclaw-qwen36-mtp4-128k.service
LOG_DIR="$ROOT/logs"
RESULT_DIR="$ROOT/results"
mkdir -p "$LOG_DIR" "$RESULT_DIR"

sudo_cmd() {
  printf 'hhtele\n' | sudo -S "$@"
}

cleanup() {
  set +e
  pkill -f 'llama-server .*--port 19343' || true
  pkill -f 'llama-server.*19343' || true
  sudo_cmd systemctl start "$SERVICE"
  sleep 8
  {
    echo "RESTORE_STATUS $(date -Is)"
    systemctl is-active "$SERVICE" || true
    systemctl is-enabled "$SERVICE" || true
    curl -sS -m 15 http://127.0.0.1:18343/v1/models | head -c 1000 || true
    echo
    nvidia-smi --query-gpu=name,driver_version,memory.total,memory.used,memory.free,utilization.gpu,power.draw,power.limit --format=csv,noheader || true
  } > "$LOG_DIR/restore-status.log" 2>&1
}
trap cleanup EXIT

{
  echo "EVAL_START $(date -Is)"
  echo "SERVICE_BEFORE"
  systemctl is-active "$SERVICE" || true
  systemctl is-enabled "$SERVICE" || true
  echo "GPU_BEFORE"
  nvidia-smi --query-gpu=name,driver_version,memory.total,memory.used,memory.free,utilization.gpu,power.draw,power.limit --format=csv,noheader || true
} > "$LOG_DIR/pre-eval-status.log" 2>&1

sudo_cmd systemctl stop "$SERVICE"
sleep 8
pkill -f 'llama-server .*--port 19343' || true
pkill -f 'llama-server.*19343' || true

python3 "$ROOT/qwen4090_pr22673_deep_eval.py" --out-dir "$RESULT_DIR"

