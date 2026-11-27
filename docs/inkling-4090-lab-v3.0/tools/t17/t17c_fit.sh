#!/usr/bin/env bash
# T17 / G4 (user decision 2026-11-27: the longest context the 4090 fits; 128K is not required).
# Which capacities allocate and run, without and with the DSpark draft: a 64-token corpus prompt
# and 8 generated tokens at ASTRAL_CTX = C (the session allocates the whole capacity up front:
# target KV, draft KV, workspaces, graphs). Peak memory.used sampled every 200 ms.
# Then the longest fitting DSpark level of 64K / 128K runs the real C - 128 token prompt of the
# t17b gen run at that level (128 tokens) and is compared with its plain greedy output.
set -u
source "$HOME/inkling-lab-v3/env.sh"
A1="$MODELS/unsloth/Mainline_Support/Inkling-2-Mini-UD-Q4_K_XL.gguf"; CK="$MODELS/inkling-native"
AST="$LAB/src/astral/target/release/astral"; PY="$LAB/venv/bin/python"; I="$LAB/runs/t17/inputs"
B=$(cat "$LAB/runs/t17/LATEST_B" 2>/dev/null || true)
O="$LAB/runs/t17/$(date -u +%Y%m%dT%H%M%SZ)-fit"; mkdir -p "$O"; echo "$O" > "$LAB/runs/t17/LATEST_FIT"
st() { echo "$1 rc=$2" >> "$O/STATUS"; }
guard; st guard-start $?
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
for C in 65536 98304 131072 132096; do run plain$C env ASTRAL_CTX=$C "$AST" generate "$A1" 8 $P64; done
for C in 32768 49152 65536 69632 73728 77824 81920 98304 114688 131072 132096; do run spec$C env ASTRAL_CTX=$C "$AST" spec-generate "$A1" "$CK" 6 8 $P64; done
for L in 131072 65536; do
  awk -F'\t' -v t=spec$L '$1 == t && $2 == 0 {f = 1} END {exit !f}' "$O/fit.tsv" || continue
  [ -n "$B" ] && [ -e "$B/gen$((L / 1024)).log" ] || break
  "$PY" -I -c "import json,sys; print(' '.join(map(str, json.load(open(sys.argv[1]))[:int(sys.argv[2])])))" "$I/ids.json" $((L - 128)) > "$O/p$((L / 1024))k.ids"
  run speclong$((L / 1024)) env ASTRAL_CTX=$((L + 64)) "$AST" spec-generate "$A1" "$CK" 6 128 @"$O/p$((L / 1024))k.ids"
  cp "$B/gen$((L / 1024)).log" "$O/plain$((L / 1024)).log"; echo "$((L / 1024))" > "$O/speclong_level"
  break
done
guard; st guard-end $?
echo DONE >> "$O/STATUS"
"$PY" -I - "$O" <<'EOF'
import os, re, sys
o = sys.argv[1]
used, total = map(int, open(os.path.join(o, "mem_idle.txt")).read().split(","))
print("idle %d MiB of %d MiB" % (used, total))
print("tag | rc | s | peak MiB | last log line")
for line in open(os.path.join(o, "fit.tsv")):
    tag, rc, sec, peak = line.rstrip("\n").split("\t")
    log = open(os.path.join(o, tag + ".log")).read().strip().splitlines()
    print("%s | %s | %s | %s | %s" % (tag, rc, sec, peak, (log[-1] if log else "")[:150]))
lv = os.path.join(o, "speclong_level")
if os.path.exists(lv):
    k = open(lv).read().strip()
    tok = lambda t: [int(x) for x in re.search(r"tokens: \[([^\]]*)\]", t).group(1).split(",")] if re.search(r"tokens: \[", t) else []
    a, b = tok(open(os.path.join(o, "plain%s.log" % k)).read()), tok(open(os.path.join(o, "speclong%s.log" % k)).read())
    same = next((i for i, (x, y) in enumerate(zip(a, b)) if x != y), min(len(a), len(b)))
    print("DSpark at %sK: greedy equal to plain for the first %d of %d tokens" % (k, same, min(len(a), len(b))))
EOF
