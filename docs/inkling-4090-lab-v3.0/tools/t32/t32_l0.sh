#!/usr/bin/env bash
# T32 (L0, plan 12 section 16.4): loop signal measurements.
# (a) A4 (varloop) with its own DSpark draft against plain decode, T21 protocol (t21_cost.sh with
#     MODEL / CKPT; configurations plain and burst).
# (b) loop self-speculation: astral ls-diag (fork df7f95b) on A4 and A1, the T21 chat
#     prompts (sn + sc) with 256 greedy tokens each and the 16K continuations (ln + lc) with 128:
#     per step the full-depth pick and the pick after pass 1 and 2 (coda + head on that pass's output,
#     real coda history). Control: the same runs without ASTRAL_LS_DIAG give the same full-depth picks.
#     Prefix property: astral trace at R = 1 and R = 3 on the same positions, the per-visit records of
#     the prelude and the first core pass (visits 0..17) must be identical.
# (c) AD01 pilot: not here (needs the L-P1 task data).
set -u
source "$HOME/inkling-lab-v3/env.sh"
A1="$MODELS/unsloth/Mainline_Support/Inkling-2-Mini-UD-Q4_K_XL.gguf"; A4="$MODELS/varloop-native"
AST="${AST:-$LAB/src/astral/target/release/astral}"; PY="$LAB/venv/bin/python"; T="$LAB/pkg/tools/t32"
T21=$(cat "$LAB/runs/t21/LATEST"); C="$(cat $LAB/runs/t19/LATEST_C)"
O="$LAB/runs/t32/$(date -u +%Y%m%dT%H%M%SZ)"; mkdir -p "$O/a4_dspark"; echo "$O" > "$LAB/runs/t32/LATEST"
st() { echo "$1 rc=$2" >> "$O/STATUS"; }
guard || exit 3; st guard-start 0
{ git -C "$(dirname "$(dirname "$(dirname "$AST")")")" rev-parse HEAD; git -C "$(dirname "$(dirname "$(dirname "$AST")")")" status --short; sha256sum "$AST"; } > "$O/identity.txt"
# (b) prompts
"$PY" -I - "$T21/ids.json" "$O" <<'EOF'
import json, sys
o = sys.argv[2]
for e in json.load(open(sys.argv[1])):
    gen = 256 if e["set"] in ("sn", "sc") else 128
    open("%s/p_%s_%s.ids" % (o, e["set"], e["case"]), "w").write(" ".join(map(str, e["ids"])) + "\n")
    open("%s/p_%s_%s.gen" % (o, e["set"], e["case"]), "w").write(str(gen))
EOF
st prompts $?
for m in a4 a1; do
  M=$A1; [ $m = a4 ] && M=$A4
  for f in "$O"/p_*.ids; do
    b=$(basename "$f" .ids); n=$(wc -w < "$f")
    ASTRAL_LS_DIAG=1 ASTRAL_LS_GEN=$(cat "$O/$b.gen") "$AST" ls-diag "$M" $((n - 1)) @"$f" > "$O/$m.$b.jsonl" 2> "$O/$m.$b.log" || st "$m-$b" $?
  done
  st ls-$m 0
  # control: three sn and three sc prompts without the diagnosis
  for f in $(ls "$O"/p_sn_*.ids | head -3) $(ls "$O"/p_sc_*.ids | head -3); do
    b=$(basename "$f" .ids); n=$(wc -w < "$f")
    ASTRAL_LS_GEN=$(cat "$O/$b.gen") "$AST" ls-diag "$M" $((n - 1)) @"$f" > "$O/$m.$b.off.jsonl" 2> /dev/null || st "$m-$b-off" $?
  done
  st ctl-$m 0
done
# prefix property: R = 1 vs R = 3, trace of the first 4 set-C sequences (decode-only probes)
head -4 "$C/manifest_c.tsv" > "$O/m4.tsv"
for m in a4 a1; do
  M=$A1; [ $m = a4 ] && M=$A4
  for R in 1 3; do ASTRAL_PASSES=$R ASTRAL_TRACE_LENS=0 "$AST" trace "$M" "$O/m4.tsv" "$O/tr_${m}_r$R" > "$O/tr_${m}_r$R.log" 2>&1; st "trace-$m-r$R" $?; done
done
# (a) A4 + its DSpark, T21 protocol
MODEL="$A4" CKPT="$A4" OUTROOT="$O/a4_dspark" CONFIGS="plain burst" REPS=2 bash "$LAB/pkg/tools/t21/t21_cost.sh" > "$O/a4_dspark.txt" 2>&1; st a4-dspark $?
"$PY" -I "$T/t32_report.py" "$O" > "$O/report.txt" 2>&1; st report $?
guard; st guard-end $?
echo DONE >> "$O/STATUS"
cat "$O/report.txt"
