#!/usr/bin/env bash
set -Eeuo pipefail

RUN_DIR="/home/hhtele/unlimited-ocr-4090"
DATA_DIR="/data/ocr"
MODEL_ROOT="/data/models/ocr/unlimited-ocr"
MODEL_DIR="$MODEL_ROOT/hf"
IMAGE="unlimited-ocr-transformers:cu121-py312"
LOG_DIR="$DATA_DIR/logs/prepare"
EXPECTED_SIZE="6672547120"

printf 'hhtele\n' | sudo -S mkdir -p \
  "$RUN_DIR" \
  "$MODEL_ROOT" \
  "$DATA_DIR/input/repo-samples" \
  "$DATA_DIR/input/user-testimg" \
  "$DATA_DIR/output/repo-samples" \
  "$DATA_DIR/output/user-testimg" \
  "$DATA_DIR/tmp" \
  "$LOG_DIR"
printf 'hhtele\n' | sudo -S chown -R hhtele:hhtele "$RUN_DIR" "$MODEL_ROOT" "$DATA_DIR"

{
  echo "PREPARE_AT $(date -Is)"
  hostname
  nvidia-smi --query-gpu=name,driver_version,memory.total,memory.used,memory.free,utilization.gpu,power.draw,temperature.gpu --format=csv,noheader,nounits
  df -h /data
  docker --version
  docker info --format '{{.ServerVersion}} {{.Runtimes}}' || true
} > "$LOG_DIR/preflight.log" 2>&1

docker build -t "$IMAGE" "$RUN_DIR" 2>&1 | tee "$LOG_DIR/docker-build.log"

docker run --rm -i --gpus all "$IMAGE" python - <<'PY' 2>&1 | tee "$LOG_DIR/gpu-smoke.log"
import torch
print("torch", torch.__version__)
print("cuda_available", torch.cuda.is_available())
print("device", torch.cuda.get_device_name(0))
print("capability", torch.cuda.get_device_capability(0))
PY

if [[ ! -f "$MODEL_DIR/model-00001-of-000001.safetensors" ]]; then
  docker run --rm -i \
    -e HF_ENDPOINT=https://hf-mirror.com \
    -v "$MODEL_ROOT:/models" \
    "$IMAGE" \
    python - <<'PY' 2>&1 | tee "$LOG_DIR/model-download.log"
from huggingface_hub import snapshot_download
snapshot_download(
    "baidu/Unlimited-OCR",
    local_dir="/models/hf",
    local_dir_use_symlinks=False,
    ignore_patterns=["assets/long-horizon-ocr.gif"],
)
PY
else
  echo "MODEL_ALREADY_PRESENT $MODEL_DIR/model-00001-of-000001.safetensors" | tee "$LOG_DIR/model-download.log"
fi

actual_size="$(stat -c '%s' "$MODEL_DIR/model-00001-of-000001.safetensors")"
echo "MODEL_SIZE $actual_size" | tee "$LOG_DIR/model-size.log"
if [[ "$actual_size" != "$EXPECTED_SIZE" ]]; then
  echo "unexpected model size: $actual_size expected $EXPECTED_SIZE" >&2
  exit 1
fi

cp "$MODEL_DIR/assets/baidu.png" "$DATA_DIR/input/repo-samples/baidu.png"
chmod +x "$RUN_DIR/ocr_run_once.sh"
python3 -m py_compile "$RUN_DIR/run_ocr.py"

echo "PREPARE_DONE $(date -Is)" | tee "$LOG_DIR/done.log"
