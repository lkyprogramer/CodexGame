#!/usr/bin/env bash
# T17 stage 1-2 within 8K: the SWA ring and the lifted MAX_CTX limits. Expected bit-identical:
#  (a) new build, ring (default) and no ring (ASTRAL_NO_SWA_RING=1), vs the previous build
#      (fork 02259e1, saved as $LAB/bin/astral-02259e1) on m8 (step / prefill / decode at the window,
#      ring-wrap, chunk and old-capacity lengths; a prefix of s0 after s0 in the same session);
#  (b) the same prefix in a fresh session (no state leaks across reset);
#  (c) prefill chunks of 1 and 777 tokens (rings of 1088 and 1856 rows): ring vs no ring;
#  (d) DSpark verify passes of 2 / 3 / 4 / 5 / 7 / 8 rows (k = 1 / 2 / 3 / 4 / 6 / 7; adaptive k <= 6 uses
#      3 / 5 / 7) after the ring wrapped: ring vs no ring vs old build;
#  (e) 8183 / 8191 / 8192 / 8193 (past the old limit) with a ring: step vs no ring.
# Reported, not bit-compared: prefill vs step at chunk 1 / 777 (logit_compare) and the same-KV
# attention reconstruction of the probes (trace, prefill to 1024, validate all).
set -u
source "$HOME/inkling-lab-v3/env.sh"
A1="$MODELS/unsloth/Mainline_Support/Inkling-2-Mini-UD-Q4_K_XL.gguf"; CK="$MODELS/inkling-native"
AST="$LAB/src/astral/target/release/astral"; OLD="$LAB/bin/astral-02259e1"; PY="$LAB/venv/bin/python"
BC="$LAB/src/astral/bench/llamacpp_compare"; U="$LAB/pkg/tools/t17/t17_util.py"; I="$LAB/runs/t17/inputs"
O="$LAB/runs/t17/$(date -u +%Y%m%dT%H%M%SZ)-a"; mkdir -p "$O"; echo "$O" > "$LAB/runs/t17/LATEST_A"
st() { echo "$1 rc=$2" >> "$O/STATUS"; }
guard; st guard-start $?
{ git -C "$LAB/src/astral" rev-parse HEAD; git -C "$LAB/src/astral" status --short; sha256sum "$AST" "$OLD"; cat "$I/SHA256"; } > "$O/identity.txt"
dfl() { local tag=$1 bin=$2 man=$3; shift 3; env "$@" "$bin" dump-final-logits "$A1" "$I/$man" "$O/$tag" > "$O/$tag.log" 2>&1; st "$tag" $?; }
dfl old "$OLD" m8.tsv
dfl ring "$AST" m8.tsv
dfl noring "$AST" m8.tsv ASTRAL_NO_SWA_RING=1
dfl fresh "$AST" m8_fresh.tsv
dfl t1ring "$AST" m8_tmax.tsv ASTRAL_TMAX=1 ASTRAL_DUMP_KINDS=prefill,decode
dfl t1noring "$AST" m8_tmax.tsv ASTRAL_TMAX=1 ASTRAL_DUMP_KINDS=prefill,decode ASTRAL_NO_SWA_RING=1
dfl t777ring "$AST" m8_tmax.tsv ASTRAL_TMAX=777
dfl t777noring "$AST" m8_tmax.tsv ASTRAL_TMAX=777 ASTRAL_NO_SWA_RING=1
dfl edge "$AST" m8_edge.tsv ASTRAL_DUMP_KINDS=step,decode
dfl edgenoring "$AST" m8_edge.tsv ASTRAL_DUMP_KINDS=step,decode ASTRAL_NO_SWA_RING=1
for k in 1 2 3 4 6 7; do
  for v in ring noring old; do
    b="$AST"; e=(); [ $v = old ] && b="$OLD"; [ $v = noring ] && e=(ASTRAL_NO_SWA_RING=1)
    env ASTRAL_SPEC_FIXED=1 "${e[@]}" "$b" dump-verify-logits "$A1" "$CK" $k "$I/v8.tsv" "$O/v$k$v" > "$O/v$k$v.log" 2>&1; st "verify$k-$v" $?
  done
  "$PY" -I "$U" rows "$O/v${k}ring/verify$k.tsv" > "$O/v${k}_rows.json"
done
ASTRAL_TRACE_PREFILL=1 ASTRAL_TRACE_VALIDATE=all "$AST" trace "$A1" "$I/tr8.tsv" "$O/trace8" > "$O/trace8.log" 2>&1; st trace8 $?
cmpdir() {  # <label> <dir a> <dir b> <kind>
  local n=0 d=0
  for f in "$2"/*."$4".f32; do [ -e "$f" ] || continue; b=$(basename "$f"); n=$((n+1)); cmp -s "$f" "$3/$b" || d=$((d+1)); done
  echo "$1 [$4]: $d of $n differ"
}
{ for k in step prefill decode; do
    cmpdir "ring vs old build" "$O/ring" "$O/old" $k; cmpdir "no ring vs old build" "$O/noring" "$O/old" $k
  done
  for f in "$O"/fresh/*.f32; do b=$(basename "$f"); cmp -s "$f" "$O/ring/$b" && echo "fresh session vs after s0, $b: same" || echo "fresh session vs after s0, $b: DIFFER"; done
  for k in prefill decode; do cmpdir "chunk 1, ring vs no ring" "$O/t1ring" "$O/t1noring" $k; done
  for k in step prefill decode; do cmpdir "chunk 777, ring vs no ring" "$O/t777ring" "$O/t777noring" $k; done
  for k in step decode; do cmpdir "8183-8193, ring vs no ring" "$O/edge" "$O/edgenoring" $k; done
  for f in "$O"/edge/e0_8183.step.f32; do cmp -s "$f" "$O/ring/s0_8183.step.f32" && echo "8183 step in an 8201-position session vs old capacity: same" || echo "8183 step vs old: DIFFER"; done
  for k in 1 2 3 4 6 7; do cmpdir "verify $k, ring vs no ring" "$O/v${k}ring" "$O/v${k}noring" verify$k; cmpdir "verify $k, ring vs old build" "$O/v${k}ring" "$O/v${k}old" verify$k; done
} > "$O/bitwise.txt"
for t in 1 777; do
  "$PY" -I "$BC/logit_compare.py" compare "$I/m8_tmax.tsv" "$O/t777ring:step" "$O/t${t}ring:prefill" "$O/pf_t$t.jsonl" > "$O/pf_t$t.json"
done
"$PY" -I "$BC/logit_compare.py" compare "$I/m8.tsv" "$O/ring:step" "$O/ring:prefill" "$O/pf_m8.jsonl" > "$O/pf_m8.json"
"$PY" -I "$LAB/pkg/tools/t15/t15_summary.py" "$O/trace8/trace.jsonl" > "$O/trace8_summary.txt" 2>&1
guard; st guard-end $?
echo DONE >> "$O/STATUS"
cat "$O/bitwise.txt"; head -3 "$O/trace8_summary.txt"
