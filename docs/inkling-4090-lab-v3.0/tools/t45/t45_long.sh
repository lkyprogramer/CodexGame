#!/usr/bin/env bash
# T45 / K12: decode tok/s at long context, decode-as-verify (default) vs ASTRAL_DECODE_LEGACY=1
# (separate decode kernels, attention one chunk per split over the whole capacity). Plain
# generate, 64 tokens after a T17-corpus prompt of L tokens, L = 1K / 32K / 128K (130944).
# usage: t45_long.sh
set -u
source "$HOME/inkling-lab-v3/env.sh"
A1="$MODELS/unsloth/Mainline_Support/Inkling-2-Mini-UD-Q4_K_XL.gguf"; AST="$LAB/src/astral/target/release/astral"; PY="$LAB/venv/bin/python"
O="$LAB/runs/t45/$(date -u +%Y%m%dT%H%M%SZ)-long"; mkdir -p "$O"; echo "$O" > "$LAB/runs/t45/LATEST_LONG"
guard || exit 3
ids() { "$PY" -I -c "import json,sys; print(' '.join(map(str, json.load(open(sys.argv[1]))[int(sys.argv[3]):int(sys.argv[3])+int(sys.argv[2])])))" "$LAB/runs/t17/inputs/ids.json" "$1" "$2"; }
for L in 1000 32768 130944; do
  off=$([ $L -le 1000 ] && echo 200000 || echo 0)
  for m in mt legacy mt legacy; do
    e=(X=1); [ $m = legacy ] && e=(ASTRAL_DECODE_LEGACY=1)
    env "${e[@]}" ASTRAL_CTX=$((L + 128)) "$AST" generate "$A1" 64 $(ids $L $off) > "$O/$L.$m.log" 2>&1
    echo "$L $m rc=$? $(grep -iE "decode|tok/s" "$O/$L.$m.log" | tail -1)"
  done
done | tee "$O/summary.txt"
guard || exit 3
