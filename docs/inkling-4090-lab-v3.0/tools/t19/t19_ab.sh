#!/usr/bin/env bash
# A/B prefill time: base binary vs fixed binary, interleaved, warm prefill via ASTRAL_WARM_PREFILL.
set -u
source "$HOME/inkling-lab-v3/env.sh"
A1="$MODELS/unsloth/Mainline_Support/Inkling-2-Mini-UD-Q4_K_XL.gguf"
O="$(cat $LAB/runs/t19nd/LATEST)"; IDS=$(head -1 "$O/m.tsv" | cut -f3 | cut -d' ' -f1-38)
for k in 16 128 512; do for r in $(seq 1 ${REPS:-8}); do for b in base fix; do
  echo "$b $k $(ASTRAL_WARM_PREFILL=$k ASTRAL_CTX=8192 "$LAB/runs/astral-$b" generate "$A1" 2 $IDS 2>&1 | grep -o 'prefill [0-9]* tokens: [0-9.]*' | awk '{print $4}')"
done; done; done | tee "$O/ab.txt"
