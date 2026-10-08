#!/usr/bin/env bash
# Capture W=6 boot error and T07 dflash W8 boot transcript. Does not leave prod down.
set -euo pipefail
HOST=hhtele@192.168.10.29
SCRATCH="${1:?scratch dir}"
WRAP='WRAP=/home/hhtele/qwen38-dflash2-20260819/launch/sudo-wrap.sh'
scp -o ConnectTimeout=15 "$(dirname "$0")/4090_test_start.sh" "$HOST:/tmp/4090_test_start.sh"
ssh -o ConnectTimeout=15 "$HOST" 'chmod +x /tmp/4090_test_start.sh'

echo "=== W6 BOOT $(date -Iseconds) ===" | tee "$SCRATCH/w6-boot.log"
set +e
ssh -o ConnectTimeout=25 "$HOST" 'NINFER_SPEC=mtp DRAFT_TOKENS=6 NINFER_CTX=200192 NINFER_KV=rk4v4-e8 bash /tmp/4090_test_start.sh' 2>&1 | tee -a "$SCRATCH/w6-boot.log"
echo "W6_EXIT=${PIPESTATUS[0]}" | tee -a "$SCRATCH/w6-boot.log"
ssh -o ConnectTimeout=15 "$HOST" 'docker logs ninfer-4090 2>&1 | tail -n 40' >> "$SCRATCH/w6-boot.log" || true
set -e

echo "=== T07 DFLASH W8 $(date -Iseconds) ===" | tee "$SCRATCH/t07-boot.log"
echo "CMD: NINFER_SPEC=dflash DRAFT_TOKENS=8 NINFER_CTX=200192 NINFER_KV=rk4v4-e8 NINFER_LMHEAD=0 bash /tmp/4090_test_start.sh" | tee -a "$SCRATCH/t07-boot.log"
echo "184K_PATH: HTTP POST /v1/chat/completions max_tokens=32 after ready; skipped if boot fails" | tee -a "$SCRATCH/t07-boot.log"
set +e
ssh -o ConnectTimeout=25 "$HOST" 'NINFER_SPEC=dflash DRAFT_TOKENS=8 NINFER_CTX=200192 NINFER_KV=rk4v4-e8 NINFER_LMHEAD=0 bash /tmp/4090_test_start.sh' 2>&1 | tee -a "$SCRATCH/t07-boot.log"
echo "T07_EXIT=${PIPESTATUS[0]}" | tee -a "$SCRATCH/t07-boot.log"
ssh -o ConnectTimeout=15 "$HOST" 'docker logs ninfer-4090 2>&1' >> "$SCRATCH/t07-boot.log" || true
set -e

# restore
ssh -o ConnectTimeout=20 "$HOST" "$WRAP; docker rm -f ninfer-4090 >/dev/null 2>&1 || true; \$WRAP systemctl start openclaw-qwen38-ninfer.service || true"
echo "W6_T07_DONE restore issued"
