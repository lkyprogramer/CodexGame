#!/usr/bin/env bash
# T17 stages 3-4: long prefill against the reference and the 16K / 32K / 64K / 128K ladder.
#  16K, 32K: llama.cpp b12751 KLD bases (-ub 128, dense relative-bias path) and its own -ub 1
#    control (N0) on the T17 corpus, one chunk each (8191 / 16383 scored positions); Astral
#    token-by-token and serving path (prefill of the first half, then decode); V4 at 32K = G4.
#  all levels, no external reference past 32K: perplexity of the same last 4095 corpus tokens
#    with 16K..128K of context (serving path); prefill vs prefill-then-decode at C-63 and C;
#    the probes' same-KV attention reconstruction at position C-1 (prefill, then a probed step);
#    prompt (C - 128 tokens) prefill time, decode speed and peak memory (nvidia-smi, 200 ms);
#    pass-key retrieval through astral serve (--no-draft) at 32K / 64K / 128K, depths 0.1 / 0.5 / 0.9;
#    at 32K, DSpark (k = 6) greedy against plain greedy for 128 tokens.
set -u
source "$HOME/inkling-lab-v3/env.sh"
A1="$MODELS/unsloth/Mainline_Support/Inkling-2-Mini-UD-Q4_K_XL.gguf"; CK="$MODELS/inkling-native"
AST="$LAB/src/astral/target/release/astral"; BIN="$LAB/src/llama.cpp/build/bin"; PY="$LAB/venv/bin/python"
export BC="$LAB/src/astral/bench/llamacpp_compare"; U="$LAB/pkg/tools/t17/t17_util.py"; I="$LAB/runs/t17/inputs"
O="$LAB/runs/t17/$(date -u +%Y%m%dT%H%M%SZ)-b"; mkdir -p "$O"; echo "$O" > "$LAB/runs/t17/LATEST_B"
st() { echo "$1 rc=$2" >> "$O/STATUS"; }
guard; st guard-start $?
{ git -C "$LAB/src/astral" rev-parse HEAD; git -C "$LAB/src/astral" status --short; git -C "$LAB/src/llama.cpp" rev-parse HEAD; cat "$I/SHA256"; } > "$O/identity.txt"
nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits > "$O/mem_idle.txt"
# run <tag> <cmd...>: wall time and peak memory.used (MiB) into $O/res.tsv
run() {
  local tag=$1; shift
  nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits -lms 200 > "$O/$tag.mem" & local mp=$!
  local t0=$(date +%s.%N); "$@" > "$O/$tag.log" 2>&1; local rc=$?; local t1=$(date +%s.%N)
  kill $mp; wait $mp 2>/dev/null
  printf '%s\t%s\t%.1f\t%s\n' "$tag" $rc "$(awk -v a="$t0" -v b="$t1" 'BEGIN {print b - a}')" "$(sort -n "$O/$tag.mem" | tail -1)" >> "$O/res.tsv"; st "$tag" $rc
}
for C in 16384 32768; do k=$((C / 1024))
  run llama$k-ub128 "$BIN/llama-perplexity" -m "$A1" -ngl 99 -f "$I/corpus.txt" -c $C --chunks 1 -ub 128 --kl-divergence-base "$O/base$k.bin"
  run llama$k-ub1 "$BIN/llama-perplexity" -m "$A1" -ngl 99 -f "$I/corpus.txt" -c $C --chunks 1 -ub 1 --kl-divergence-base "$O/ub1_$k.bin"
  run astral$k-step "$AST" dump-logits "$A1" "$O/base$k.bin" "$O/step$k.bin"
  run astral$k-serve env ASTRAL_DUMP_PREFILL=1 "$AST" dump-logits "$A1" "$O/base$k.bin" "$O/serve$k.bin"
  "$PY" -I "$BC/kld_compare.py" "$O/base$k.bin" "$O/ub1_$k.bin" > "$O/n0_$k.json"
  "$PY" -I "$BC/kld_compare.py" "$O/base$k.bin" "$O/step$k.bin" > "$O/step$k.json"
  "$PY" -I "$BC/kld_compare.py" "$O/base$k.bin" "$O/serve$k.bin" > "$O/serve$k.json"
  "$PY" -I "$BC/kld_compare.py" "$O/step$k.bin" "$O/serve$k.bin" > "$O/step_vs_serve$k.json"
done; st kld $?
for C in 16384 32768 65536 131072; do k=$((C / 1024))
  run ladder$k env ASTRAL_DUMP_PREFILL=1 "$AST" dump-logits "$A1" "$I/tok${k}k.bin" "$O/ladder$k.bin"
  "$PY" -I "$U" ppl "$O/ladder$k.bin" 4095 > "$O/ladder$k.json"
  run lf$k env ASTRAL_DUMP_KINDS=prefill,decode "$AST" dump-final-logits "$A1" "$I/lf${k}k.tsv" "$O/lf$k"
  "$PY" -I "$BC/logit_compare.py" compare "$I/lf${k}k.tsv" "$O/lf$k:prefill" "$O/lf$k:decode" "$O/lf$k.jsonl" > "$O/lf$k.json"
  run trace$k env ASTRAL_TRACE_PREFILL=1 ASTRAL_TRACE_VALIDATE=all "$AST" trace "$A1" "$I/tr${k}k.tsv" "$O/trace$k"
  "$PY" -I "$LAB/pkg/tools/t15/t15_summary.py" "$O/trace$k/trace.jsonl" > "$O/trace$k.txt" 2>&1
  IDS=$("$PY" -I -c "import json,sys; print(' '.join(map(str, json.load(open(sys.argv[1]))[:int(sys.argv[2])])))" "$I/ids.json" $((C - 128)))
  run gen$k env ASTRAL_CTX=$((C + 64)) "$AST" generate "$A1" 128 $IDS
done
rm -f "$O"/*.bin
# DSpark at 32K: the prompt of gen32 (32640 tokens)
"$PY" -I -c "import json,sys; print(' '.join(map(str, json.load(open(sys.argv[1]))[:32640])))" "$I/ids.json" > "$O/p32k.ids"
run spec32 env ASTRAL_CTX=32832 "$AST" spec-generate "$A1" "$CK" 6 128 @"$O/p32k.ids"
# pass-key retrieval through the server
bash "$LAB/pkg/tools/t17/t17_needle.sh" "$O"; st needle $?
"$PY" -I "$LAB/pkg/tools/t17/t17_report.py" "$O" > "$O/report.txt" 2>&1; st report $?
guard; st guard-end $?
echo DONE >> "$O/STATUS"
cat "$O/report.txt"
