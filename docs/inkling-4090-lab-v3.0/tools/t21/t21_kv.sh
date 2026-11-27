#!/usr/bin/env bash
# T21 draft KV compaction: (1) the ring for the draft's sliding-window layers is bit-identical
# (spec-generate tokens and round counts vs ASTRAL_DRAFT_KV_FULL=1 and vs the previous build,
# short prompts and a 16K-token prompt); (2) the largest DSpark context with the ring, f32 and
# f16 (ASTRAL_DRAFT_KV_F16=1): spec-generate at capacity N with an (N - 600)-token prompt from
# the T17 corpus, 256 tokens, ascending N until the first failure; decode speed and acceptance
# at each N. usage: t21_kv.sh [old binary]
set -u
source "$HOME/inkling-lab-v3/env.sh"
A1="$MODELS/unsloth/Mainline_Support/Inkling-2-Mini-UD-Q4_K_XL.gguf"; NAT="$MODELS/inkling-native"; R="$LAB/runs"
NEW="$LAB/src/astral/target/release/astral"; OLD="${1:-$LAB/bin/astral-k2b}"
O="$(cat "$R/t21/LATEST")/kv-$(date -u +%Y%m%dT%H%M%SZ)"; mkdir -p "$O"; W=$(cat "$R/w2/LATEST")
guard || exit 3
sha256sum "$NEW" "$OLD" > "$O/bin.sha256"; git -C "$LAB/src/astral" diff > "$O/src.diff"
h() { grep -o 'tokens: .*' "$1" | md5sum | cut -c1-8; }
st() { grep -o 'decode [0-9]* tok in .*' "$1" | head -1; }
python3 - "$R/t17/inputs/ids.json" "$O" << 'EOF'
import json, sys
ids = json.load(open(sys.argv[1]))
open(sys.argv[2] + "/l16k.ids", "w").write(" ".join(map(str, ids[100000:116384])))
for n in (77824, 90112, 98304, 106496, 114688, 122880, 131072):
    open(sys.argv[2] + "/cap%d.ids" % n, "w").write(" ".join(map(str, ids[:n - 600])))
EOF
{
echo "== bit identity (ring vs full vs old build)"
for p in "$W/t13/p00.ids" "$W/t13/p03.ids" "$O/l16k.ids"; do
  b=$(basename "$p" .ids)
  ASTRAL_SPEC_NO_CHECK=1 ASTRAL_SPEC_REPS=1 "$NEW" spec-generate "$A1" "$NAT" 6 512 "@$p" > "$O/id-$b-ring.log" 2>&1
  ASTRAL_DRAFT_KV_FULL=1 ASTRAL_SPEC_NO_CHECK=1 ASTRAL_SPEC_REPS=1 "$NEW" spec-generate "$A1" "$NAT" 6 512 "@$p" > "$O/id-$b-full.log" 2>&1
  ASTRAL_SPEC_NO_CHECK=1 ASTRAL_SPEC_REPS=1 "$OLD" spec-generate "$A1" "$NAT" 6 512 "@$p" > "$O/id-$b-old.log" 2>&1
  echo "$b ring $(h "$O/id-$b-ring.log") full $(h "$O/id-$b-full.log") old $(h "$O/id-$b-old.log") | ring: $(st "$O/id-$b-ring.log") | old: $(st "$O/id-$b-old.log")"
done
echo "== capacity (DSpark, k 6, 256 tokens)"
for mode in f32 f16; do
  for n in 77824 90112 98304 106496 114688 122880 131072; do
    e=(X=1); [ $mode = f16 ] && e=(ASTRAL_DRAFT_KV_F16=1)
    env "${e[@]}" ASTRAL_CTX=$n ASTRAL_SPEC_NO_CHECK=1 ASTRAL_SPEC_REPS=1 "$NEW" spec-generate "$A1" "$NAT" 6 256 "@$O/cap$n.ids" > "$O/cap-$mode-$n.log" 2>&1; rc=$?
    echo "$mode $n rc=$rc $(st "$O/cap-$mode-$n.log") $(grep -m1 -io 'out of memory\|error.*' "$O/cap-$mode-$n.log" | head -c 160)"
    [ $rc -ne 0 ] && break
  done
done
} 2>&1 | tee "$O/summary.txt"
guard
