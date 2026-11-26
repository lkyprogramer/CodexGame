#!/usr/bin/env bash
# T19 re-run, stage 2 (CPU): repeatability, then num-3 (rule_num3.json, frozen before this run)
# on set C (verdict) and sets A / B (description), plus num-2 on all sets for the record.
set -u
source "$HOME/inkling-lab-v3/env.sh"
O="${1:-$(cat $LAB/runs/t19/LATEST_C)}"; cd "$O"
PY="$LAB/venv/bin/python"; LC="$LAB/src/astral/bench/llamacpp_compare/logit_compare.py"; T="$LAB/pkg/tools/t19"
sha256sum "$T/rule_num3.json" "$T/rule_num2.json" > rules.sha256
for k in step prefill; do d=0; n=0; for f in as1/*.$k.f32; do n=$((n+1)); cmp -s "$f" "as2/$(basename "$f")" || d=$((d+1)); done; echo "astral $k repeat: $d of $n differ"; done > repeat.txt
: > verdicts.txt
for s in a b c; do
  "$PY" -I "$LC" compare manifest_$s.tsv ll:single ll:batch ref_shape_$s.jsonl > ref_shape_$s.json
  "$PY" -I "$LC" compare manifest_$s.tsv as1:step as1:prefill astral_shape_$s.jsonl > astral_shape_$s.json
  "$PY" -I "$LC" judge-paired manifest_$s.tsv astral_shape_$s.jsonl ref_shape_$s.jsonl "$T/rule_num3.json" > num3_$s.json; echo "num-3 set $s rc=$?" >> verdicts.txt
  "$PY" -I "$LC" judge manifest_$s.tsv astral_shape_$s.jsonl "$T/rule_num2.json" > num2_$s.json; echo "num-2 set $s rc=$?" >> verdicts.txt
  "$PY" -I "$LC" compare manifest_$s.tsv ll:single as1:step cross_step_$s.jsonl > cross_step_$s.json
  "$PY" -I "$LC" compare manifest_$s.tsv ll:batch as1:prefill cross_prefill_$s.jsonl > cross_prefill_$s.json
done
cat repeat.txt verdicts.txt
