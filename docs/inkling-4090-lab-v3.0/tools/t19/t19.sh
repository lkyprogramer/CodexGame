#!/usr/bin/env bash
# T19 stage 1 (GPU): dump raw logits from llama.cpp (single / batch, single twice) and Astral
# (step / prefill, twice) for the manifests from t19_manifest.py. No comparison of Astral
# results happens here; the rule is calibrated and frozen from the llama.cpp data first.
set -u
source "$HOME/inkling-lab-v3/env.sh"
O="$LAB/runs/t19/$(date -u +%Y%m%dT%H%M%SZ)"; mkdir -p "$O"; echo "$O" > "$LAB/runs/t19/LATEST"
A1="$MODELS/unsloth/Mainline_Support/Inkling-2-Mini-UD-Q4_K_XL.gguf"
AST="$LAB/src/astral/target/release/astral"; FL="$LAB/runs/final_logits"
st() { echo "$1 rc=$2" >> "$O/STATUS"; }
guard; st guard-start $?
"$LAB/venv/bin/python" -I "$LAB/pkg/tools/t19/t19_manifest.py" "$(cat $LAB/runs/w1/LATEST)" "$(cat $LAB/runs/w2/LATEST)" "$(cat $LAB/runs/t14/LATEST)" "$O" > "$O/manifest.json"; st manifest $?
M="$O/manifest_ab.tsv"
{ git -C "$LAB/src/astral" rev-parse HEAD; git -C "$LAB/src/llama.cpp" rev-parse HEAD; sha256sum "$M" "$O"/manifest_a.tsv "$O"/manifest_b.tsv; } > "$O/identity.txt"
mkdir -p "$O/ll1" "$O/ll2" "$O/as1" "$O/as2"
"$FL" "$A1" "$M" "$O/ll1" single > "$O/ll1-single.log" 2>&1; st ll1-single $?
"$FL" "$A1" "$M" "$O/ll1" batch > "$O/ll1-batch.log" 2>&1; st ll1-batch $?
"$FL" "$A1" "$M" "$O/ll2" single > "$O/ll2-single.log" 2>&1; st ll2-single $?
"$AST" dump-final-logits "$A1" "$M" "$O/as1" > "$O/as1.log" 2>&1; st as1 $?
"$AST" dump-final-logits "$A1" "$M" "$O/as2" > "$O/as2.log" 2>&1; st as2 $?
guard; st guard-end $?
echo DONE >> "$O/STATUS"
