#!/usr/bin/env bash
# T16 round 1 (K2): decode attention-input projections on tensor cores (multi_mma) vs dp4a
# (multi). (1) speed: generate 512 tokens at 1K / 7K tokens of context, alternating, 3 times;
# (2) the code change equals the environment switch bit for bit (new default vs previous binary
# with ASTRAL_DECODE_DP4A=1, new with ASTRAL_DECODE_MMA=1 vs previous default) on the T17 m8
# manifest. G2 / G3 afterwards: t16_g2.sh. usage: t16_k2.sh <previous binary>
set -u
source "$HOME/inkling-lab-v3/env.sh"
A1="$MODELS/unsloth/Mainline_Support/Inkling-2-Mini-UD-Q4_K_XL.gguf"; NEW="$LAB/src/astral/target/release/astral"; OLD=$1; PY="$LAB/venv/bin/python"
O="$LAB/runs/t16/k2-$(date -u +%Y%m%dT%H%M%SZ)"; mkdir -p "$O"; echo "$O" > "$LAB/runs/t16/LATEST_K2"
guard || exit 3
sha256sum "$NEW" "$OLD" > "$O/bin.sha256"
for L in 1000 7000; do
  IDS=$("$PY" -I -c "import json,sys; print(' '.join(map(str, json.load(open(sys.argv[1]))[200000:200000+int(sys.argv[2])])))" "$LAB/runs/t17/inputs/ids.json" $L)
  for r in 1 2 3; do for v in mma dp4a; do
    e=(ASTRAL_DECODE_MMA=1); [ $v = dp4a ] && e=(ASTRAL_DECODE_DP4A=1)
    env "${e[@]}" "$NEW" generate "$A1" 512 $IDS > "$O/$v-$L-$r.log" 2>&1
    echo "$L $v $r $(grep -o 'decode [0-9]* tok at [0-9.]* tok/s' "$O/$v-$L-$r.log") $(grep -o 'tokens: \[[^]]*' "$O/$v-$L-$r.log" | md5sum | cut -c1-8)"
  done; done
done | tee "$O/ab.txt"
M="$LAB/runs/t17/inputs/m8.tsv"; K=ASTRAL_DUMP_KINDS=step,decode
env $K "$NEW" dump-final-logits "$A1" "$M" "$O/new" > "$O/new.log" 2>&1
env $K ASTRAL_DECODE_DP4A=1 "$OLD" dump-final-logits "$A1" "$M" "$O/olddp4a" > "$O/olddp4a.log" 2>&1
env $K ASTRAL_DECODE_MMA=1 "$NEW" dump-final-logits "$A1" "$M" "$O/newmma" > "$O/newmma.log" 2>&1
env $K "$OLD" dump-final-logits "$A1" "$M" "$O/old" > "$O/old.log" 2>&1
cmpd() { n=0; d=0; for f in "$2"/*.f32; do n=$((n+1)); cmp -s "$f" "$3/$(basename "$f")" || d=$((d+1)); done; echo "$1: $d of $n differ"; }
{ cmpd "new default vs previous + ASTRAL_DECODE_DP4A" "$O/new" "$O/olddp4a"; cmpd "new + ASTRAL_DECODE_MMA vs previous default" "$O/newmma" "$O/old"; cmpd "new default vs previous default" "$O/new" "$O/old"; } | tee "$O/bitwise.txt"
guard
