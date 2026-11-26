#!/usr/bin/env bash
# T20 coverage, stage 1 (GPU): set-B continuations and set-D documents, logit dumps from
# llama.cpp (single / batch) and Astral (step / prefill / decode; DSpark verify with k = 1, 3, 7,
# i.e. 2, 4 and 8 rows per pass), and free-running greedy for strict token agreement.
# Analysis: t20_judge.sh.
set -u
source "$HOME/inkling-lab-v3/env.sh"
A1="$MODELS/unsloth/Mainline_Support/Inkling-2-Mini-UD-Q4_K_XL.gguf"; NATIVE="$MODELS/inkling-native"
AST="$LAB/src/astral/target/release/astral"; FL="$LAB/runs/final_logits"; BIN="$LAB/src/llama.cpp/build/bin"
PY="$LAB/venv/bin/python"; T="$LAB/pkg/tools/t20"; BC="$LAB/src/astral/bench/llamacpp_compare"; PORT=18998
DOCS="$LAB/src/llama.cpp/docs"
O="$LAB/runs/t20/$(date -u +%Y%m%dT%H%M%SZ)"; mkdir -p "$O/bseq"; echo "$O" > "$LAB/runs/t20/LATEST"
st() { echo "$1 rc=$2" >> "$O/STATUS"; }
wait_up() { for i in $(seq 1 300); do curl -sf http://127.0.0.1:$PORT/health >/dev/null && return 0; sleep 1; done; return 1; }
stop() { kill $1 2>/dev/null; wait $1 2>/dev/null; sleep 3; }
guard; st guard-start $?
"$AST" serve "$A1" --checkpoint "$NATIVE" --no-draft --host 127.0.0.1 --port $PORT --ctx 8192 > "$O/ids-server.log" 2>&1 & SP=$!
wait_up && "$PY" -I "$T/t20_ids.py" http://127.0.0.1:$PORT "$O/ids_b.json" b "$(cat $LAB/runs/t14/LATEST)/ids.json" > "$O/ids.txt" \
  && "$PY" -I "$T/t20_ids.py" http://127.0.0.1:$PORT "$O/ids_d.json" d "$DOCS/build.md" "$DOCS/autoparser.md" "$DOCS/speculative.md" "$DOCS/function-calling.md+$DOCS/multimodal.md" >> "$O/ids.txt"; st ids $?
stop $SP
"$BIN/llama-server" -m "$A1" -ngl 99 -c 4096 --host 127.0.0.1 --port $PORT -np 1 > "$O/llama-server.log" 2>&1 & SP=$!
wait_up && "$PY" -I "$BC/greedy_reference.py" http://127.0.0.1:$PORT "$O/ids_b.json" "$O/bseq" 160 > "$O/bseq.txt" 2>&1; st bseq $?
stop $SP
"$PY" -I "$T/t20_manifest.py" "$O/ids_b.json" "$O/bseq" "$O/ids_d.json" "$O" > "$O/manifest.json"; st manifest $?
{ git -C "$LAB/src/astral" rev-parse HEAD; git -C "$LAB/src/astral" status --short; git -C "$LAB/src/llama.cpp" rev-parse HEAD; sha256sum "$O"/manifest_*.tsv "$LAB/pkg/tools/t19/rule_num3.json"; } > "$O/identity.txt"
mkdir -p "$O/ll" "$O/as" "$O/as2" "$O/vf"
"$FL" "$A1" "$O/manifest_bd.tsv" "$O/ll" single > "$O/ll-single.log" 2>&1; st ll-single $?
"$FL" "$A1" "$O/manifest_bd.tsv" "$O/ll" batch > "$O/ll-batch.log" 2>&1; st ll-batch $?
"$AST" dump-final-logits "$A1" "$O/manifest_bd.tsv" "$O/as" > "$O/as.log" 2>&1; st as $?
"$AST" dump-final-logits "$A1" "$O/manifest_d.tsv" "$O/as2" > "$O/as2.log" 2>&1; st as2-repeat-d $?
for K in 1 3 7; do
  ASTRAL_SPEC_FIXED=1 "$AST" dump-verify-logits "$A1" "$NATIVE" $K "$O/manifest_b.tsv" "$O/vf" > "$O/vf$K.log" 2>&1; st verify-k$K $?
done
# Free-running greedy (prefill -> decode), 160 tokens per set-B prompt, against llama.cpp's.
for i in $(seq -w 0 15); do
  "$PY" -I -c "import json,sys; print(' '.join(map(str, json.load(open(sys.argv[1]))[int(sys.argv[2])]['ids'])))" "$O/ids_b.json" $((10#$i)) > "$O/bprompt_$i.ids"
  "$AST" generate "$A1" 160 $(cat "$O/bprompt_$i.ids") > "$O/gen_$i.txt" 2>&1 || st gen-$i $?
done
st generate 0
guard; st guard-end $?
echo DONE >> "$O/STATUS"
