#!/usr/bin/env bash
set -Eeuo pipefail

RUN_DIR="/home/hhtele/unlimited-ocr-4090"
SERVICE="openclaw-qwen36-mtp4-128k.service"
IMAGE="unlimited-ocr-transformers:cu121-py312"
MODEL_HOST="/data/models/ocr/unlimited-ocr/hf"
DATA_HOST="/data/ocr"
TOKEN="${QWEN_NGINX_TOKEN:-}"
OCR_TIMEOUT_SECONDS="${OCR_TIMEOUT_SECONDS:-300}"

GROUP=""
INPUT=""
MODE="auto"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --group) GROUP="$2"; shift 2 ;;
    --input) INPUT="$2"; shift 2 ;;
    --mode) MODE="$2"; shift 2 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done

if [[ -z "$GROUP" || -z "$INPUT" ]]; then
  echo "usage: $0 --group <group> --input <path> [--mode auto|gundam|base]" >&2
  exit 2
fi

if [[ ! -f "$INPUT" ]]; then
  echo "input not found: $INPUT" >&2
  exit 2
fi

stem="$(basename "$INPUT")"
ext="${stem##*.}"
name="${stem%.*}"
safe_name="$(printf '%s_%s' "$name" "$ext" | tr -c 'A-Za-z0-9_.-' '_')"
OUT_HOST="$DATA_HOST/output/$GROUP/$safe_name"
LOG_DIR="$DATA_HOST/logs/$GROUP/$safe_name"
mkdir -p "$OUT_HOST" "$LOG_DIR"

case "$INPUT" in
  /data/ocr/*) INPUT_CONT="/work/${INPUT#/data/ocr/}" ;;
  *) echo "input must be under /data/ocr: $INPUT" >&2; exit 2 ;;
esac
OUT_CONT="/work/output/$GROUP/$safe_name"

restore_service() {
  set +e
  docker rm -f unlimited-ocr-active >/dev/null 2>&1 || true
  printf 'hhtele\n' | sudo -S systemctl start "$SERVICE" >/dev/null 2>&1
  sleep 10
  {
    echo "RESTORE_AT $(date -Is)"
    systemctl is-active "$SERVICE"
    systemctl is-enabled "$SERVICE"
    echo "LOCAL_18343"
    curl -sS -m 60 http://127.0.0.1:18343/v1/models
    echo
    if [[ -n "$TOKEN" ]]; then
      echo "LOCAL_28343_AUTH"
      curl -sS -m 60 -H "Authorization: Bearer $TOKEN" http://127.0.0.1:28343/v1/models
      echo
    else
      echo "LOCAL_28343_AUTH_SKIPPED"
    fi
    echo "LOCAL_28343_NOAUTH_STATUS"
    curl -sS -m 60 -o "$LOG_DIR/noauth-body.json" -w "%{http_code}" http://127.0.0.1:28343/v1/models
    echo
    echo "OCR_RESIDUAL"
    docker ps --format '{{.ID}} {{.Image}} {{.Names}}' | grep -E 'unlimited-ocr|unlimited-ocr-active' || true
    ps -eo pid,ppid,stat,pcpu,pmem,args | grep -E 'run_ocr.py|Unlimited-OCR' | grep -v grep || true
    echo "GPU"
    nvidia-smi --query-gpu=name,driver_version,memory.total,memory.used,memory.free,utilization.gpu,power.draw,temperature.gpu --format=csv,noheader,nounits
  } > "$LOG_DIR/restore.log" 2>&1
}

trap restore_service EXIT INT TERM

{
  echo "START_AT $(date -Is)"
  echo "GROUP $GROUP"
  echo "INPUT $INPUT"
  echo "OUTPUT $OUT_HOST"
  file "$INPUT" || true
  stat -c 'SIZE_BYTES %s' "$INPUT" || true
  systemctl is-active "$SERVICE" || true
  systemctl is-enabled "$SERVICE" || true
  nvidia-smi --query-gpu=name,driver_version,memory.total,memory.used,memory.free,utilization.gpu,power.draw,temperature.gpu --format=csv,noheader,nounits
} > "$LOG_DIR/preflight.log" 2>&1

printf 'hhtele\n' | sudo -S systemctl stop "$SERVICE" >/dev/null
for _ in $(seq 1 90); do
  used="$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | tr -d ' ')"
  [[ "${used:-99999}" -lt 2500 ]] && break
  sleep 1
done

sample_flag="$LOG_DIR/gpu-sample.flag"
touch "$sample_flag"
(
  while [[ -f "$sample_flag" ]]; do
    printf '%s,' "$(date -Is)"
    nvidia-smi --query-gpu=memory.used,memory.free,utilization.gpu,power.draw,temperature.gpu --format=csv,noheader,nounits
    sleep 1
  done
) > "$LOG_DIR/gpu-samples.csv" 2>/dev/null &
sampler_pid=$!

set +e
started="$(date +%s)"
timeout --foreground "$OCR_TIMEOUT_SECONDS" docker run --rm \
  --name unlimited-ocr-active \
  --gpus all \
  --ipc=host \
  --network none \
  --shm-size=8g \
  -e TRANSFORMERS_OFFLINE=1 \
  -v "$MODEL_HOST:/models/unlimited-ocr:ro" \
  -v "$DATA_HOST:/work" \
  "$IMAGE" \
  python /app/run_ocr.py \
    --model /models/unlimited-ocr \
    --group "$GROUP" \
    --input "$INPUT_CONT" \
    --output "$OUT_CONT" \
    --mode "$MODE" 2>&1 | tee "$LOG_DIR/ocr.log"
ocr_rc="${PIPESTATUS[0]}"
finished="$(date +%s)"
set -e

rm -f "$sample_flag"
wait "$sampler_pid" 2>/dev/null || true

{
  echo "OCR_RC $ocr_rc"
  echo "ELAPSED_S $((finished - started))"
  echo "TIMEOUT_SECONDS $OCR_TIMEOUT_SECONDS"
  echo "OUTPUT $OUT_HOST"
  find "$OUT_HOST" -maxdepth 4 -type f | sort
} > "$LOG_DIR/result.log" 2>&1

exit "$ocr_rc"
