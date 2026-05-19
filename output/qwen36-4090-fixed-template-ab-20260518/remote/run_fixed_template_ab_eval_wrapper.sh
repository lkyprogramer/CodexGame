#!/usr/bin/env bash
set -euo pipefail

RUN_DIR="/home/hhtele/qwen36-fixed-template-ab-20260518"
RESULT_DIR="$RUN_DIR/results"
SERVICE="openclaw-qwen36-mtp4-128k.service"
TOKEN="${QWEN_NGINX_TOKEN:-}"

mkdir -p "$RESULT_DIR"

cleanup() {
  set +e
  pkill -f "llama-server.*19343" || true
  printf 'hhtele\n' | sudo -S systemctl start "$SERVICE" >/tmp/qwen36_fixed_template_restore.log 2>&1
  sleep 4
  systemctl is-active "$SERVICE" >"$RESULT_DIR/service_active_after.txt" 2>&1
  systemctl is-enabled "$SERVICE" >"$RESULT_DIR/service_enabled_after.txt" 2>&1
  curl -sS http://127.0.0.1:18343/v1/models >"$RESULT_DIR/backend_models_after.json" 2>&1 || true
  if [[ -n "$TOKEN" ]]; then
    curl -sS -H "Authorization: Bearer $TOKEN" http://127.0.0.1:28343/v1/models >"$RESULT_DIR/nginx_models_after.json" 2>&1 || true
  fi
}
trap cleanup EXIT

systemctl is-active "$SERVICE" >"$RESULT_DIR/service_active_before.txt" 2>&1 || true
systemctl is-enabled "$SERVICE" >"$RESULT_DIR/service_enabled_before.txt" 2>&1 || true
curl -sS http://127.0.0.1:18343/v1/models >"$RESULT_DIR/backend_models_before.json" 2>&1 || true

printf 'hhtele\n' | sudo -S systemctl stop "$SERVICE"
sleep 5
pkill -f "llama-server.*19343" || true

python3 "$RUN_DIR/qwen4090_fixed_template_ab_eval.py" --out-dir "$RESULT_DIR" 2>&1 | tee "$RESULT_DIR/eval.log"
