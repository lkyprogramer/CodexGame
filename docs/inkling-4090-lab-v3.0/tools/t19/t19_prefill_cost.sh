#!/usr/bin/env bash
# Prefill time with and without the split-K paths (warm, astral generate ASTRAL_WARM_PREFILL).
set -u
source "$HOME/inkling-lab-v3/env.sh"
A1="$MODELS/unsloth/Mainline_Support/Inkling-2-Mini-UD-Q4_K_XL.gguf"
AST="$LAB/src/astral/target/release/astral"
O="$(cat $LAB/runs/t19nd/LATEST)"; IDS=$(head -1 "$O/m.tsv" | cut -f3 | cut -d' ' -f1-38)
for cfg in default BOTH; do
  case $cfg in default) envs=() ;; BOTH) envs=(ASTRAL_NO_SPLITK=1 ASTRAL_SGEMM_NO_SPLIT=1) ;; esac
  for k in 16 38 128 512 2048 7000; do
    for r in 1 2 3; do
      echo "$cfg $k $r $(env "${envs[@]}" ASTRAL_WARM_PREFILL=$k ASTRAL_CTX=8192 "$AST" generate "$A1" 2 $IDS 2>&1 | grep -o 'prefill [0-9]* tokens: [0-9.]* ms')"
    done
  done
done | tee "$O/prefill_cost.txt"
