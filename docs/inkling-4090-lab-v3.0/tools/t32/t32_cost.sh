#!/usr/bin/env bash
# T32 supplement: per-pass cost of A4 for the LS / AD-G0 gates. T21 protocol (t21_cost.sh, MODEL /
# CKPT = A4) with ASTRAL_PASSES=1 (plain) and ASTRAL_PASSES=2 (plain, burst: the lossy "all 2 passes"
# point B1, with and without A4's DSpark); and spec-generate after a 100,000-token prompt (T17 corpus,
# ctx 106496) at ASTRAL_PASSES=1 / 2 / 3, for the plain decode speed by depth at long context.
set -u
source "$HOME/inkling-lab-v3/env.sh"
A4="$MODELS/varloop-native"; AST="$LAB/src/astral/target/release/astral"; PY="$LAB/venv/bin/python"
O="$(cat "$LAB/runs/t32/LATEST")/cost"; mkdir -p "$O"
guard || exit 3
ASTRAL_PASSES=1 MODEL="$A4" CKPT="$A4" OUTROOT="$O/r1" CONFIGS="plain" REPS=2 bash "$LAB/pkg/tools/t21/t21_cost.sh" > "$O/r1.txt" 2>&1; echo "r1 rc=$?" >> "$O/STATUS"
ASTRAL_PASSES=2 MODEL="$A4" CKPT="$A4" OUTROOT="$O/r2" CONFIGS="plain burst" REPS=2 bash "$LAB/pkg/tools/t21/t21_cost.sh" > "$O/r2.txt" 2>&1; echo "r2 rc=$?" >> "$O/STATUS"
"$PY" -I -c "import json,sys; print(' '.join(map(str, json.load(open(sys.argv[1]))[:100000])))" "$LAB/runs/t17/inputs/ids.json" > "$O/p100k.ids"
for R in 1 2 3; do
  ASTRAL_PASSES=$R ASTRAL_CTX=106496 "$AST" spec-generate "$A4" "$A4" 6 128 @"$O/p100k.ids" > "$O/long_r$R.txt" 2>&1; echo "long-r$R rc=$?" >> "$O/STATUS"
done
guard
for f in r1 r2; do echo "== $f"; grep -A 4 "^== decode" "$O/$f.txt"; grep -A 2 "^== speedup" "$O/$f.txt"; done
for R in 1 2 3; do echo "== long R=$R"; grep -E "^run|^plain" "$O/long_r$R.txt"; done
