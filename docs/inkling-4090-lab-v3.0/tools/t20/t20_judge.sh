#!/usr/bin/env bash
# T20 stage 2 (CPU): num-3 (tools/t19/rule_num3.json, frozen in T19) per path, candidate Astral
# step vs <path>, reference llama.cpp single vs batch on the same positions; cross-engine and
# strict-token summaries. usage: t20_judge.sh [run dir]
set -u
source "$HOME/inkling-lab-v3/env.sh"
O="${1:-$(cat $LAB/runs/t20/LATEST)}"; cd "$O"
PY="$LAB/venv/bin/python"; LC="$LAB/src/astral/bench/llamacpp_compare/logit_compare.py"; R3="$LAB/pkg/tools/t19/rule_num3.json"
sha256sum "$R3" > rules.sha256
d=0; n=0; for f in as2/*.f32; do n=$((n+1)); cmp -s "$f" "as/$(basename "$f")" || d=$((d+1)); done; echo "astral set-d repeat: $d of $n files differ" > repeat.txt
: > verdicts.txt
pair() {  # <label> <manifest> <astral kind dir:kind>
  "$PY" -I "$LC" compare "$2" ll:single ll:batch "ref_$1.jsonl" > "ref_$1.json"
  "$PY" -I "$LC" compare "$2" as:step "$3" "cand_$1.jsonl" > "cand_$1.json"
  "$PY" -I "$LC" judge-paired "$2" "cand_$1.jsonl" "ref_$1.jsonl" "$R3" > "num3_$1.json"; echo "num-3 $1 rc=$?" >> verdicts.txt
}
pair b_prefill manifest_b.tsv as:prefill
pair b_decode manifest_b_gen.tsv as:decode
for K in 1 3 7; do pair b_verify$K manifest_b_gen.tsv vf:verify$K; done
pair d_prefill manifest_d.tsv as:prefill
pair d_decode manifest_d_gen.tsv as:decode
# Cross-engine (description): the serving paths against llama.cpp token-by-token.
"$PY" -I "$LC" compare manifest_b_gen.tsv ll:single as:decode cross_b_decode.jsonl > cross_b_decode.json
"$PY" -I "$LC" compare manifest_b_gen.tsv ll:single vf:verify3 cross_b_verify3.jsonl > cross_b_verify3.json
"$PY" -I "$LC" compare manifest_d.tsv ll:single as:prefill cross_d_prefill.jsonl > cross_d_prefill.json
"$PY" -I "$LC" compare manifest_d.tsv ll:single as:step cross_d_step.jsonl > cross_d_step.json
"$PY" -I "$LAB/pkg/tools/t20/t20_report.py" . > report.txt 2>&1
cat repeat.txt verdicts.txt report.txt
