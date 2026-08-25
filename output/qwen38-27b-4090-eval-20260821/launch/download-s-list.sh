#!/usr/bin/env bash
# Parallel hf-mirror downloads. Does not touch GPU or 18343.
set -euo pipefail

HF="${HF_ENDPOINT:-https://hf-mirror.com}"
EVAL="${EVAL_DIR:-/data/models/qwen/qwen38-eval}"
LOG="${LOG_DIR:-/home/hhtele/qwen38-27b-4090-eval-20260821/logs}"
mkdir -p "$EVAL"/{templates,grug-v1.1,fable-distill,salience-r5,cold-fusion-v1.1} "$LOG"

download() {
  local repo="$1" file="$2" dest="$3"
  local url="${HF}/${repo}/resolve/main/${file}"
  mkdir -p "$dest"
  echo "[$(date -u +%FT%TZ)] START $file" | tee -a "$LOG/download.log"
  aria2c -c -x 8 -s 8 --file-allocation=none \
    -d "$dest" -o "$file" \
    --console-log-level=notice \
    "$url" >>"$LOG/aria2-${file}.log" 2>&1
  local rc=$?
  if [[ $rc -ne 0 ]]; then
    echo "[$(date -u +%FT%TZ)] FAIL $file rc=$rc" | tee -a "$LOG/download.log"
    return $rc
  fi
  (cd "$dest" && sha256sum "$file" | tee "$dest/${file}.sha256")
  cat "$dest/${file}.sha256" >>"$LOG/download.log"
  echo "[$(date -u +%FT%TZ)] DONE $file" | tee -a "$LOG/download.log"
}

# Tiny jinja first so Sharp smoke can start immediately.
download peculiar-ragdoll/Qwen-Sharp-Chat-Templates \
  chat_template.jinja \
  "$EVAL/templates"

download ProCreations/grug-v1.1-qwen-3.8-27b-gguf \
  grug-27b-v1.1-Q4_K_M.gguf \
  "$EVAL/grug-v1.1" &
p1=$!

download TeichAI/Qwen3.8-27B-Fable-Distill-GGUF \
  Qwen3.8-27B-Fable-Distill-Q4_K_M.gguf \
  "$EVAL/fable-distill" &
p2=$!

download bartowski/vectionlabs_Salience-27B-R5-GGUF \
  vectionlabs_Salience-27B-R5-Q4_K_M.gguf \
  "$EVAL/salience-r5" &
p3=$!

download DavidAU/Qwen3.8-27B-Cold-Fusion-GAIN-V1.1-NM-DAU-NEO-MAX-MTP-GGUF \
  Qwen3.8-27B-Cold-Fusion-GAIN-V1.1-NM-DAU-NEO-MAX-NEO-MTP-Q4_K_M.gguf \
  "$EVAL/cold-fusion-v1.1" &
p4=$!

fail=0
for p in $p1 $p2 $p3 $p4; do
  if ! wait "$p"; then
    fail=1
  fi
done
if [[ $fail -ne 0 ]]; then
  echo "[$(date -u +%FT%TZ)] SOME DOWNLOADS FAILED" | tee -a "$LOG/download.log"
  exit 1
fi
echo "[$(date -u +%FT%TZ)] ALL DOWNLOADS OK" | tee -a "$LOG/download.log"
find "$EVAL" -name '*.sha256' -print0 | sort -z | xargs -0 cat | tee "$EVAL/SHA256SUMS" | tee -a "$LOG/download.log"
