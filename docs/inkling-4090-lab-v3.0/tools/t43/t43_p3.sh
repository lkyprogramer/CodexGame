#!/usr/bin/env bash
# T43 Phase 3: DFlash2 at long context and maximum capacity. The DFlash2 draft keeps only a
# 2048 + 8 (or tmax) row ring per layer, so its memory does not grow with the context; DSpark has
# one global layer and stops at 114688 (T25). Part 1: which capacities allocate and run with
# DFlash2 (64-token prompt, 8 tokens, peak memory.used). Part 2: real prompts of L - 128 tokens
# (T17 corpus) at L = 32K / 64K / 128K, 128 generated tokens, k = 7, DFlash2 and (where it fits)
# DSpark; spec-generate also decodes plainly and reports how long the speculative output equals
# the plain greedy one, and the teacher-forced mismatches. usage: t43_p3.sh
set -u
source "$HOME/inkling-lab-v3/env.sh"
A1="$MODELS/unsloth/Mainline_Support/Inkling-2-Mini-UD-Q4_K_XL.gguf"; DF="$MODELS/dflash2"; CK="$MODELS/inkling-native"
AST="$LAB/src/astral/target/release/astral"; PY="$LAB/venv/bin/python"; I="$LAB/runs/t17/inputs"
O="$LAB/runs/t43/$(date -u +%Y%m%dT%H%M%SZ)-p3"; mkdir -p "$O"; echo "$O" > "$LAB/runs/t43/LATEST_P3"
st() { echo "$1 rc=$2" >> "$O/STATUS"; }
guard || exit 3
{ git -C "$LAB/src/astral" rev-parse HEAD; git -C "$LAB/src/astral" status --short; sha256sum "$AST"; } > "$O/identity.txt"
nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader,nounits > "$O/mem_idle.txt"
run() {
  local tag=$1; shift
  nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits -lms 200 > "$O/$tag.mem" & local mp=$!
  local t0=$(date +%s.%N); "$@" > "$O/$tag.log" 2>&1; local rc=$?; local t1=$(date +%s.%N)
  kill $mp; wait $mp 2>/dev/null
  printf '%s\t%s\t%.1f\t%s\n' "$tag" $rc "$(awk -v a="$t0" -v b="$t1" 'BEGIN {print b - a}')" "$(sort -n "$O/$tag.mem" | tail -1)" >> "$O/fit.tsv"; st "$tag" $rc
}
P64=$("$PY" -I -c "import json,sys; print(' '.join(map(str, json.load(open(sys.argv[1]))[:64])))" "$I/ids.json")
for C in 114688 122880 131072 132096; do run df2fit$C env ASTRAL_CTX=$C "$AST" spec-generate "$A1" "$DF" 7 8 $P64; done
for L in 32768 65536 131072; do
  K=$((L / 1024)); "$PY" -I -c "import json,sys; print(' '.join(map(str, json.load(open(sys.argv[1]))[:int(sys.argv[2])])))" "$I/ids.json" $((L - 128)) > "$O/p${K}k.ids"
  run df2long$K env ASTRAL_CTX=$((L + 64)) "$AST" spec-generate "$A1" "$DF" 7 128 @"$O/p${K}k.ids"
  [ $L -le 114688 ] && run dsplong$K env ASTRAL_CTX=$((L + 64)) "$AST" spec-generate "$A1" "$CK" 7 128 @"$O/p${K}k.ids"
done
guard; st guard-end $?
echo DONE >> "$O/STATUS"
"$PY" -I - "$O" <<'EOF' | tee "$O/summary.txt"
import os, sys
o = sys.argv[1]
used, total = map(int, open(os.path.join(o, "mem_idle.txt")).read().split(","))
print("idle %d MiB of %d MiB" % (used, total))
for line in open(os.path.join(o, "fit.tsv")):
    tag, rc, sec, peak = line.rstrip("\n").split("\t")
    log = [l for l in open(os.path.join(o, tag + ".log")).read().splitlines() if l.startswith(("run 1", "plain", "teacher", "error"))]
    print("%s | rc %s | %s s | peak %s MiB" % (tag, rc, sec, peak))
    for l in log:
        print("    " + l[:200])
EOF
