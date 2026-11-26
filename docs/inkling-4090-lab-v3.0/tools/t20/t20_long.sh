#!/usr/bin/env bash
# T20 long context, dense: llama.cpp perplexity KLD protocol at c4096 x 4 chunks (scored
# positions 2048-4094 of each chunk, 8188 in all) on the W1 corpus. Reference control N0:
# llama.cpp -ub 1 against its own -ub 512 base, same file; Astral token-by-token (step) and the
# serving path (prefill of the first 2048 tokens, then decode). V4's approved formula
# (05 section 3) is applied with this N0. Large .bin files are deleted after the comparison.
set -u
source "$HOME/inkling-lab-v3/env.sh"
A1="$MODELS/unsloth/Mainline_Support/Inkling-2-Mini-UD-Q4_K_XL.gguf"
AST="$LAB/src/astral/target/release/astral"; BIN="$LAB/src/llama.cpp/build/bin"; PY="$LAB/venv/bin/python"
KC="$LAB/src/astral/bench/llamacpp_compare/kld_compare.py"
W1=$(cat "$LAB/runs/w1/LATEST"); CORPUS="$(ls -d "$W1"/golden/*-golden | tail -1)/corpus.txt"
O="$(cat $LAB/runs/t20/LATEST)/long"; mkdir -p "$O"
st() { echo "$1 rc=$2" >> "$O/STATUS"; }
guard; st guard-start $?
"$BIN/llama-perplexity" -m "$A1" -ngl 99 -f "$CORPUS" -c 4096 --chunks 4 --kl-divergence-base "$O/base.bin" > "$O/base.log" 2>&1; st llama-ub512 $?
"$BIN/llama-perplexity" -m "$A1" -ngl 99 -f "$CORPUS" -c 4096 --chunks 4 -ub 1 --kl-divergence-base "$O/ub1.bin" > "$O/ub1.log" 2>&1; st llama-ub1 $?
"$AST" dump-logits "$A1" "$O/base.bin" "$O/astral_step.bin" > "$O/astral_step.log" 2>&1; st astral-step $?
ASTRAL_DUMP_PREFILL=1 "$AST" dump-logits "$A1" "$O/base.bin" "$O/astral_serve.bin" > "$O/astral_serve.log" 2>&1; st astral-serve $?
"$PY" -I "$KC" "$O/base.bin" "$O/ub1.bin" > "$O/n0.json"; st n0 $?
"$PY" -I "$KC" "$O/base.bin" "$O/astral_step.bin" > "$O/astral_step.json"; st cmp-step $?
"$PY" -I "$KC" "$O/base.bin" "$O/astral_serve.bin" > "$O/astral_serve.json"; st cmp-serve $?
"$PY" -I "$KC" "$O/ub1.bin" "$O/astral_step.bin" > "$O/ub1_vs_step.json"; st cmp-ub1-step $?
"$PY" -I "$KC" "$O/astral_step.bin" "$O/astral_serve.bin" > "$O/step_vs_serve.json"; st cmp-step-serve $?
sha256sum "$O"/*.bin > "$O/bins.sha256"; rm -f "$O"/*.bin
guard; st guard-end $?
echo DONE >> "$O/STATUS"
