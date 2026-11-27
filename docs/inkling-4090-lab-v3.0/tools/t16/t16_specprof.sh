#!/usr/bin/env bash
# T16 / v3.0.17: GPU time per DSpark round by kernel (nsys 2023.3 CUDA trace with graph nodes),
# spec-generate k = 6, 512 tokens, W1 prompts p00 and p03. The totals include the short prefill
# and the 50 draft-only replays of ASTRAL_SPEC_PROFILE (about 0.4 ms per round), and nsys slows
# the run down; use the shares, not the absolute times. usage: t16_specprof.sh
set -u
source "$HOME/inkling-lab-v3/env.sh"
A1="$MODELS/unsloth/Mainline_Support/Inkling-2-Mini-UD-Q4_K_XL.gguf"; AST="$LAB/src/astral/target/release/astral"; PY="$LAB/venv/bin/python"
O="$LAB/runs/t16/specprof-$(date -u +%Y%m%dT%H%M%SZ)"; mkdir -p "$O"; W=$(cat "$LAB/runs/w2/LATEST")
guard || exit 3
for f in p00 p03; do
  ASTRAL_SPEC_NO_CHECK=1 ASTRAL_SPEC_REPS=1 ASTRAL_SPEC_PROFILE=1 nsys profile --trace=cuda --cuda-graph-trace=node --sample=none --cpuctxsw=none -o "$O/$f" -f true "$AST" spec-generate "$A1" "$MODELS/inkling-native" 6 512 "@$W/t13/$f.ids" > "$O/$f.log" 2>&1
  nsys export --type sqlite -o "$O/$f.sqlite" -f true "$O/$f.nsys-rep" > /dev/null 2>&1
  grep -h "^run\|profile:" "$O/$f.log"
  "$PY" -I "$LAB/pkg/tools/t16/t16_round_kernels.py" "$O/$f.sqlite" "$(grep -o '[0-9]* rounds' "$O/$f.log" | head -1 | cut -d' ' -f1)" | tee "$O/$f.kernels.txt"
done
guard
