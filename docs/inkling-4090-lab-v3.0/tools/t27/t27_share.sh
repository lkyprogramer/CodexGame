#!/usr/bin/env bash
# T27 step 1: upper bound of the terminal-tail trim. Prefill time of plain prompts (T17 corpus ids)
# at 512 / 2K / 8K / 32K / 128K with the terminal layer intact, without its attention read-out
# (ASTRAL_T27_SKIP=attn) and without attention, O projection and FFN (=all). Measurement only:
# the skip modes give wrong outputs.
set -u
source "$HOME/inkling-lab-v3/env.sh"
A1="$MODELS/unsloth/Mainline_Support/Inkling-2-Mini-UD-Q4_K_XL.gguf"
AST="${AST:-$LAB/src/astral/target/release/astral}"; PY="$LAB/venv/bin/python"; I="$LAB/runs/t17/inputs"
O="$LAB/runs/t27/$(date -u +%Y%m%dT%H%M%SZ)-share"; mkdir -p "$O"; echo "$O" > "$LAB/runs/t27/LATEST"
REPS=${REPS:-2}
guard; echo "guard-start $?" >> "$O/STATUS"
{ git -C "$LAB/src/astral" rev-parse HEAD; git -C "$LAB/src/astral" diff --stat; sha256sum "$AST"; } > "$O/identity.txt"
for n in ${LENS:-512 2048 8192 32768 130944}; do
  IDS=$("$PY" -I -c "import json,sys; print(' '.join(map(str, json.load(open(sys.argv[1]))[:int(sys.argv[2])])))" "$I/ids.json" $n)
  for r in $(seq "$REPS"); do
    for m in none attn all; do
      env ASTRAL_CTX=$((n + 64)) ASTRAL_T27_SKIP=$m "$AST" generate "$A1" 2 $IDS > "$O/g$n-$m-$r.log" 2>&1
      printf '%s\t%s\t%s\t%s\n' $n $m $r "$(grep -o 'in [0-9.]* s' "$O/g$n-$m-$r.log" | tr -dc '0-9.')" >> "$O/res.tsv"
    done
  done
done
guard; echo "guard-end $?" >> "$O/STATUS"; echo DONE >> "$O/STATUS"
cat "$O/res.tsv"
