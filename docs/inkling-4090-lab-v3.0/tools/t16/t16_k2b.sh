#!/usr/bin/env bash
# T16 round 2 (K2b): Q8_0 products of 2-8-token passes on dp4a for sm_89, decode on tensor cores.
# Bit-level checks against the previous builds, then t16_g2.sh (which includes T20). Expects
# the new build in target/release and the T17 build at $LAB/bin/astral-9593eb4.
# usage: t16_k2b.sh
set -u
source "$HOME/inkling-lab-v3/env.sh"; R="$LAB/runs"
A1="$MODELS/unsloth/Mainline_Support/Inkling-2-Mini-UD-Q4_K_XL.gguf"; NEW="$LAB/src/astral/target/release/astral"; NAT="$MODELS/inkling-native"; T17B="$LAB/bin/astral-9593eb4"
O="$R/t16/k2b-$(date -u +%Y%m%dT%H%M%SZ)"; mkdir -p "$O"; echo "$O" > "$R/t16/LATEST_K2B"; W=$(cat "$R/w2/LATEST"); W1=$(cat "$R/w1/LATEST"); T=$(cat "$R/t20/LATEST")
guard || exit 3
sha256sum "$NEW" "$T17B" > "$O/bin.sha256"; git -C "$LAB/src/astral" rev-parse HEAD > "$O/identity.txt"; git -C "$LAB/src/astral" diff > "$O/src.diff"
h() { grep -o 'tokens: .*' "$1" | md5sum | cut -c1-8; }
{
for f in p00 p03; do ASTRAL_SPEC_NO_CHECK=1 ASTRAL_SPEC_REPS=1 "$NEW" spec-generate "$A1" "$NAT" 6 512 "@$W/t13/$f.ids" > "$O/spec-$f.log" 2>&1; echo "spec $f $(h "$O/spec-$f.log")"; done
grep "^b" "$T/manifest_bd.tsv" > "$O/mb.tsv"; mkdir -p "$O/new" "$O/t17"
"$NEW" dump-final-logits "$A1" "$O/mb.tsv" "$O/new" > "$O/new.log" 2>&1; "$T17B" dump-final-logits "$A1" "$O/mb.tsv" "$O/t17" > "$O/t17.log" 2>&1
for k in step decode prefill; do n=0; d=0; for f in "$O"/new/*.$k.f32; do n=$((n+1)); cmp -s "$f" "$O/t17/$(basename "$f")" || d=$((d+1)); done; echo "$k new vs 9593eb4: $d of $n differ"; done
IDS=$(tail -1 "$W1/ids.txt" | tr -d '[],')
"$NEW" generate "$A1" 128 $IDS > "$O/gen-new.log" 2>&1; ASTRAL_SMALL_TC=1 "$NEW" generate "$A1" 128 $IDS > "$O/gen-tc.log" 2>&1; "$T17B" generate "$A1" 128 $IDS > "$O/gen-t17.log" 2>&1
echo "W1 generate (5-token prompt): new $(h "$O/gen-new.log") new+SMALL_TC $(h "$O/gen-tc.log") 9593eb4 $(h "$O/gen-t17.log")"
bash "$LAB/pkg/tools/t16/t16_g2.sh" > "$O/g2.out" 2>&1; echo "g2 rc=$?"
} 2>&1 | tee "$O/summary.txt"
guard
