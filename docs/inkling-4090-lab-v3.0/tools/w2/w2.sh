#!/usr/bin/env bash
set -uo pipefail
source "$HOME/inkling-lab-v3/env.sh"
guard || { echo "DRIVER GUARD FAIL"; exit 3; }
A1="$MODELS/unsloth/Mainline_Support/Inkling-2-Mini-UD-Q4_K_XL.gguf"
AST="$LAB/src/astral/target/release/astral"; BIN="$LAB/src/llama.cpp/build/bin"; PY="$LAB/venv/bin/python"; R="$LAB/runs"
W1=$(cat "$R/w1/LATEST"); G=$(ls -d "$W1"/golden/*-golden | tail -1); BASE="$G/kld_base_c512x8.bin"; CORPUS="$G/corpus.txt"
O="$R/w2/$(date -u +%Y%m%dT%H%M%SZ)"; mkdir -p "$O/seq"; echo "$O" > "$R/w2/LATEST"
st() { echo "$1 rc=$2" | tee -a "$O/STATUS"; }
"$LAB/venv/bin/pip" install -q -i https://pypi.tuna.tsinghua.edu.cn/simple numpy > "$O/pip.txt" 2>&1; st pip $?
# V4 noise floor N0: llama.cpp -ub 1 against its own -ub 512 base
"$BIN/llama-perplexity" -m "$A1" -ngl 99 -f "$CORPUS" -c 512 --chunks 8 -ub 1 --kl-divergence-base "$O/llama_ub1.bin" > "$O/llama_ub1.log" 2>&1; st llama-ub1 $?
"$BIN/llama-perplexity" -m "$A1" -ngl 99 -f "$CORPUS" -c 512 --chunks 8 -ub 1 --kl-divergence-base "$BASE" --kl-divergence > "$O/n0_builtin.log" 2>&1; st n0-builtin $?
# V4 Astral (token-by-token decode path)
"$AST" dump-logits "$A1" "$BASE" "$O/astral_step.bin" > "$O/astral_dump.log" 2>&1; st astral-dump $?
"$PY" -I "$R/kld.py" "$BASE" "$O/llama_ub1.bin" > "$O/n0.json"; st n0 $?
"$PY" -I "$R/kld.py" "$BASE" "$O/astral_step.bin" > "$O/astral_vs_llama.json"; st astral-kld $?
# V5/V6/V7 reference: 16 chat prompts, 500 greedy tokens from llama-server
"$BIN/llama-server" -m "$A1" -ngl 99 -c 4096 --host 127.0.0.1 --port 18999 -np 1 > "$O/llama-server.log" 2>&1 &
SP=$!; for i in $(seq 1 240); do curl -sf http://127.0.0.1:18999/health >/dev/null && break; sleep 1; done
"$PY" -I "$R/refseq.py" http://127.0.0.1:18999 "$W1/v2-llama.json" "$O/seq" 500 > "$O/refseq.txt" 2>&1; st refseq $?
kill $SP; wait $SP 2>/dev/null
for f in "$O"/seq/*.ids; do
  i=$(basename "$f" .ids)
  "$AST" score "$A1" $(cat "$f") > "$O/seq/score_$i.txt" 2>&1
  "$AST" cmp-prefill "$A1" $(cat "$f") > "$O/seq/cmp_$i.txt" 2>&1
done
"$PY" -I "$R/v567.py" "$O/seq" > "$O/v567.json"; st v567 $?
guard; st guard-end $?
echo DONE
