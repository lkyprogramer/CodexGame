#!/usr/bin/env bash
# T19 follow-up: which split-K path makes Astral's prefill non-reproducible. Runs
# dump-final-logits twice per configuration on a small manifest and counts differing files.
set -u
source "$HOME/inkling-lab-v3/env.sh"
A1="$MODELS/unsloth/Mainline_Support/Inkling-2-Mini-UD-Q4_K_XL.gguf"
AST="$LAB/src/astral/target/release/astral"
O="$LAB/runs/t19nd/$(date -u +%Y%m%dT%H%M%SZ)"; mkdir -p "$O"; echo "$O" > "$LAB/runs/t19nd/LATEST"
head -4 "$(cat $LAB/runs/t19/LATEST)/manifest_a.tsv" > "$O/m.tsv"
guard; echo "guard-start rc=$?" > "$O/STATUS"
for cfg in default NO_SPLITK SGEMM_NO_SPLIT BOTH; do
  case $cfg in
    default) envs=() ;;
    NO_SPLITK) envs=(ASTRAL_NO_SPLITK=1) ;;
    SGEMM_NO_SPLIT) envs=(ASTRAL_SGEMM_NO_SPLIT=1) ;;
    BOTH) envs=(ASTRAL_NO_SPLITK=1 ASTRAL_SGEMM_NO_SPLIT=1) ;;
  esac
  for r in 1 2; do mkdir -p "$O/$cfg/$r"; env "${envs[@]}" "$AST" dump-final-logits "$A1" "$O/m.tsv" "$O/$cfg/$r" > "$O/$cfg/$r.log" 2>&1 || echo "$cfg $r failed" >> "$O/STATUS"; done
  for k in step prefill; do d=0; n=0; for f in "$O/$cfg/1"/*.$k.f32; do n=$((n+1)); cmp -s "$f" "$O/$cfg/2/$(basename "$f")" || d=$((d+1)); done; echo "$cfg $k differ $d/$n" >> "$O/STATUS"; done
done
guard; echo "guard-end rc=$?" >> "$O/STATUS"
