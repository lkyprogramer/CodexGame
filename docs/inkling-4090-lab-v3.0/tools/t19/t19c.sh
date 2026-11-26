#!/usr/bin/env bash
# T19 re-run after the prefill determinism fix (fork 35de94a), with hold-out set C for num-3.
# Stage 1 (GPU): set-C ids and greedy llama.cpp continuations, logit dumps for A + B + C
# (llama.cpp single / batch; Astral step / prefill twice), and regression checks of the fix
# (verify-model, 128-token greedy against W1). Judging is t19c_judge.sh.
set -u
source "$HOME/inkling-lab-v3/env.sh"
A1="$MODELS/unsloth/Mainline_Support/Inkling-2-Mini-UD-Q4_K_XL.gguf"
AST="$LAB/src/astral/target/release/astral"; FL="$LAB/runs/final_logits"; BIN="$LAB/src/llama.cpp/build/bin"
PY="$LAB/venv/bin/python"; T="$LAB/pkg/tools/t19"; BC="$LAB/src/astral/bench/llamacpp_compare"; PORT=18998
W1="$(cat $LAB/runs/w1/LATEST)"
O="$LAB/runs/t19/$(date -u +%Y%m%dT%H%M%SZ)-c"; mkdir -p "$O/cseq"; echo "$O" > "$LAB/runs/t19/LATEST_C"
st() { echo "$1 rc=$2" >> "$O/STATUS"; }
wait_up() { for i in $(seq 1 300); do curl -sf http://127.0.0.1:$PORT/health >/dev/null && return 0; sleep 1; done; return 1; }
stop() { kill $1 2>/dev/null; wait $1 2>/dev/null; sleep 3; }
guard; st guard-start $?
"$AST" serve "$A1" --checkpoint "$MODELS/inkling-native" --no-draft --host 127.0.0.1 --port $PORT --ctx 8192 > "$O/ids-server.log" 2>&1 & SP=$!
wait_up && "$PY" -I "$T/t19_ids_c.py" http://127.0.0.1:$PORT "$T/prompts_set_c.json" "$O/ids_c.json"; st ids-c $?
stop $SP
"$BIN/llama-server" -m "$A1" -ngl 99 -c 4096 --host 127.0.0.1 --port $PORT -np 1 > "$O/llama-server.log" 2>&1 & SP=$!
wait_up && "$PY" -I "$BC/greedy_reference.py" http://127.0.0.1:$PORT "$O/ids_c.json" "$O/cseq" 160 > "$O/cseq.txt" 2>&1; st cseq $?
stop $SP
"$PY" -I "$T/t19_manifest.py" "$W1" "$(cat $LAB/runs/w2/LATEST)" "$(cat $LAB/runs/t14/LATEST)" "$O" "$O/cseq" "$O/ids_c.json" > "$O/manifest.json"; st manifest $?
M="$O/manifest_abc.tsv"
{ git -C "$LAB/src/astral" rev-parse HEAD; git -C "$LAB/src/astral" status --short; git -C "$LAB/src/llama.cpp" rev-parse HEAD; sha256sum "$O"/manifest_*.tsv "$T/prompts_set_c.json" "$T/rule_num3.json"; } > "$O/identity.txt"
mkdir -p "$O/ll" "$O/as1" "$O/as2"
"$FL" "$A1" "$M" "$O/ll" single > "$O/ll-single.log" 2>&1; st ll-single $?
"$FL" "$A1" "$M" "$O/ll" batch > "$O/ll-batch.log" 2>&1; st ll-batch $?
"$AST" dump-final-logits "$A1" "$M" "$O/as1" > "$O/as1.log" 2>&1; st as1 $?
"$AST" dump-final-logits "$A1" "$M" "$O/as2" > "$O/as2.log" 2>&1; st as2 $?
# Regression checks of the fix against W1 (step path untouched; prefill feeds generate).
"$AST" verify-model "$A1" "$(ls -d $W1/golden/*-golden | tail -1)/eval_callback.log" > "$O/verify-model.txt" 2>&1; st verify-model $?
IDS=$(tail -1 "$W1/ids.txt" | tr -d '[],')
"$AST" generate "$A1" 128 $IDS > "$O/astral-generate.txt" 2>&1; st generate $?
guard; st guard-end $?
echo DONE >> "$O/STATUS"
