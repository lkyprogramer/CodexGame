#!/usr/bin/env bash
# T19 stage 2 (CPU): repeatability, reference shape control, and the frozen num-2 judgment of
# Astral (step = reference side, prefill = candidate) on set A (calibration) and set B (hold-out),
# plus the cross-engine comparisons for information. Rule: tools/t19/rule_num2.json (frozen
# before this script was run).
set -u
source "$HOME/inkling-lab-v3/env.sh"
O="${1:-$(cat $LAB/runs/t19/LATEST)}"; cd "$O"
PY="$LAB/venv/bin/python"; LC="$LAB/src/astral/bench/llamacpp_compare/logit_compare.py"
RULE="$LAB/pkg/tools/t19/rule_num2.json"
sha256sum "$RULE" > rule.sha256
d=0; for f in as1/*.f32; do cmp -s "$f" "as2/$(basename "$f")" || d=$((d+1)); done
echo "astral repeat: $d of $(ls as1 | wc -l) files differ" > repeat.txt
for set in a b; do
  "$PY" -I "$LC" compare manifest_$set.tsv as1:step as1:prefill astral_shape_$set.jsonl > astral_shape_$set.json
  "$PY" -I "$LC" judge manifest_$set.tsv astral_shape_$set.jsonl "$RULE" > verdict_v7_$set.json; echo "v7 set $set rc=$?" >> verdicts.txt
  "$PY" -I "$LC" compare manifest_$set.tsv ll1:single as1:step cross_step_$set.jsonl > cross_step_$set.json
  "$PY" -I "$LC" compare manifest_$set.tsv ll1:batch as1:prefill cross_prefill_$set.jsonl > cross_prefill_$set.json
done
"$PY" -I "$LC" compare manifest_b.tsv ll1:single ll1:batch ref_shape_b.jsonl > ref_shape_b.json
cat repeat.txt verdicts.txt
