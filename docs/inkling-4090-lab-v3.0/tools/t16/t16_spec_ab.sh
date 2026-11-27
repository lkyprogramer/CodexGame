#!/usr/bin/env bash
# T16 / v3.0.17: DSpark speed of the current binary, default vs one environment switch (e.g.
# ASTRAL_SMALL_DP4A=1: Q8_0 products of 2-8 rows on dp4a instead of tensor cores). spec-generate
# with k drafts, 512 tokens, on W1 prompts p00 p01 p02 p03 p06 p07 (written by w2/t13.sh), twice,
# alternating; prints tok/s, rounds, tokens per round, draft step time (ASTRAL_SPEC_PROFILE) and
# a hash of the generated tokens. usage: t16_spec_ab.sh <VAR=VALUE> [k]
set -u
source "$HOME/inkling-lab-v3/env.sh"
SW=$1; K=${2:-6}
A1="$MODELS/unsloth/Mainline_Support/Inkling-2-Mini-UD-Q4_K_XL.gguf"; AST="$LAB/src/astral/target/release/astral"
O="$LAB/runs/t16/spec-ab-$(date -u +%Y%m%dT%H%M%SZ)"; mkdir -p "$O"; W=$(cat "$LAB/runs/w2/LATEST")
guard || exit 3
{ git -C "$LAB/src/astral" rev-parse HEAD; sha256sum "$AST"; echo "switch $SW k $K"; } > "$O/identity.txt"
for r in 1 2; do for f in p00 p01 p02 p03 p06 p07; do for v in default switch; do
  e=(X=1); [ $v = switch ] && e=("$SW")
  env "${e[@]}" ASTRAL_SPEC_NO_CHECK=1 ASTRAL_SPEC_REPS=1 ASTRAL_SPEC_PROFILE=1 "$AST" spec-generate "$A1" "$MODELS/inkling-native" "$K" 512 "@$W/t13/$f.ids" > "$O/$v-$f-$r.log" 2>&1
  echo "$r $f $v $(grep -o 'decode 511 tok in [0-9.]* s = [0-9.]* tok/s; [0-9]* rounds, [0-9.]* tokens/round' "$O/$v-$f-$r.log") $(grep -o 'draft step [0-9.]* ms' "$O/$v-$f-$r.log") $(grep -o 'spec tokens: .*' "$O/$v-$f-$r.log" | md5sum | cut -c1-8)"
done; done; done | tee "$O/ab.txt"
guard
